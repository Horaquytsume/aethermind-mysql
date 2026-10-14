"""AetherMind demo backend: Flask, MySQL, secure password hashing and cookie sessions."""
from __future__ import annotations

import hmac
import json
import logging
import os
import re
import secrets
import threading
import unicodedata
from contextlib import contextmanager
from datetime import timedelta
from functools import wraps
from typing import Any, Iterator

import mysql.connector
from mysql.connector import pooling
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from recommendations import build_recommendation

load_dotenv()
_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_POOL_LOCK = threading.Lock()


def _response_error(message: str, status: int):
    return jsonify({"error": message}), status


def _normalize_text(value: Any, field: str, maximum: int, required: bool = False) -> str:
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise ValueError(f"O campo {field} deve ser texto.")
    text = unicodedata.normalize("NFKC", value)
    text = "".join(char for char in text if char in "\n\t" or unicodedata.category(char)[0] != "C")
    text = text.strip()
    if required and not text:
        raise ValueError(f"Preencha o campo {field}.")
    if len(text) > maximum:
        raise ValueError(f"O campo {field} excede {maximum} caracteres.")
    return text


def _json_object() -> dict[str, Any]:
    if not request.is_json:
        raise ValueError("Envie os dados no formato JSON.")
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ValueError("O corpo da requisição deve ser um objeto JSON.")
    return payload


def _parse_json(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value) if value else {}
    except (TypeError, json.JSONDecodeError):
        return {}


def _make_csrf_token() -> str:
    token = secrets.token_urlsafe(32)
    session["csrf_token"] = token
    return token


def _authenticated(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not isinstance(session.get("user_id"), int):
            return _response_error("Faça login para continuar.", 401)
        return view(*args, **kwargs)
    return wrapped


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    app = Flask(__name__)
    app.config.update(
        MAX_CONTENT_LENGTH=32 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        PERMANENT_SESSION_LIFETIME=timedelta(days=7),
        SESSION_REFRESH_EACH_REQUEST=True,
        MYSQL_HOST=os.getenv("MYSQL_HOST", "127.0.0.1"),
        MYSQL_PORT=int(os.getenv("MYSQL_PORT", "3306")),
        MYSQL_USER=os.getenv("MYSQL_USER", "aethermind"),
        MYSQL_PASSWORD=os.getenv("MYSQL_PASSWORD", ""),
        MYSQL_DATABASE=os.getenv("MYSQL_DATABASE", "aethermind"),
        MYSQL_POOL_SIZE=int(os.getenv("MYSQL_POOL_SIZE", "5")),
        MYSQL_SSL_CA=os.getenv("MYSQL_SSL_CA", ""),
    )
    if test_config:
        app.config.update(test_config)

    if app.config.get("TESTING") and not app.config.get("SECRET_KEY"):
        app.config["SECRET_KEY"] = "test-only-secret-key-do-not-use-in-production"
    secret_key = app.config.get("SECRET_KEY") or os.getenv("APP_SECRET_KEY")
    if not secret_key or len(str(secret_key)) < 32:
        raise RuntimeError("Defina APP_SECRET_KEY com pelo menos 32 caracteres em .env.")
    app.config["SECRET_KEY"] = secret_key
    app.config["SESSION_COOKIE_SECURE"] = (
        str(os.getenv("COOKIE_SECURE", "true" if os.getenv("APP_ENV") == "production" else "false")).lower()
        in {"1", "true", "yes", "on"}
    )
    app.logger.setLevel(logging.INFO)

    @app.before_request
    def verify_csrf() -> Any:
        if request.path.startswith("/api/") and request.method in _UNSAFE_METHODS:
            expected = session.get("csrf_token", "")
            supplied = request.headers.get("X-CSRF-Token", "")
            if not expected or not supplied or not hmac.compare_digest(expected, supplied):
                return _response_error("Sessão expirada. Atualize a página e tente novamente.", 403)
        return None

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.errorhandler(413)
    def request_too_large(_error):
        return _response_error("A requisição excede o tamanho permitido.", 413)

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(
            "Erro interno ao processar a requisição",
            exc_info=(type(error), error, error.__traceback__),
        )
        return _response_error("Ocorreu um erro interno. Tente novamente.", 500)

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/health")
    def health():
        try:
            with db_connection(app) as connection:
                cursor = connection.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                cursor.close()
            return jsonify({"status": "ok", "database": "ok"})
        except mysql.connector.Error:
            app.logger.exception("Verificação do MySQL falhou")
            return _response_error("Banco de dados indisponível.", 503)

    @app.get("/api/auth/csrf")
    def csrf_token():
        token = session.get("csrf_token") or _make_csrf_token()
        return jsonify({"csrf_token": token})

    @app.post("/api/auth/register")
    def register():
        try:
            data = _json_object()
            name = _normalize_text(data.get("name"), "nome", 120, required=True)
            email = _normalize_text(data.get("email"), "e-mail", 254, required=True).casefold()
            password = data.get("password")
            if len(name) < 2:
                raise ValueError("O nome deve ter pelo menos 2 caracteres.")
            if not _EMAIL_RE.fullmatch(email):
                raise ValueError("Informe um e-mail válido.")
            if not isinstance(password, str) or not 12 <= len(password) <= 128:
                raise ValueError("A senha deve ter entre 12 e 128 caracteres.")
            if data.get("consent") is not True:
                raise ValueError("Confirme o aviso de armazenamento dos dados para criar a conta.")
        except ValueError as exc:
            return _response_error(str(exc), 400)

        try:
            with db_connection(app) as connection:
                cursor = connection.cursor()
                cursor.execute(
                    "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s)",
                    (name, email, generate_password_hash(password)),
                )
                user_id = int(cursor.lastrowid)
                connection.commit()
                cursor.close()
        except mysql.connector.IntegrityError as exc:
            if getattr(exc, "errno", None) == 1062:
                return _response_error("Já existe uma conta com esse e-mail.", 409)
            app.logger.exception("Falha ao criar usuário")
            return _response_error("Não foi possível criar a conta agora.", 503)
        except mysql.connector.Error:
            app.logger.exception("MySQL indisponível durante cadastro")
            return _response_error("Banco de dados indisponível. Tente novamente.", 503)

        session.clear()
        session.permanent = True
        session["user_id"] = user_id
        csrf = _make_csrf_token()
        return jsonify({"user": {"id": user_id, "name": name, "email": email}, "csrf_token": csrf}), 201

    @app.post("/api/auth/login")
    def login():
        try:
            data = _json_object()
            email = _normalize_text(data.get("email"), "e-mail", 254, required=True).casefold()
            password = data.get("password")
            if not _EMAIL_RE.fullmatch(email) or not isinstance(password, str) or len(password) > 128:
                return _response_error("E-mail ou senha incorretos.", 401)
        except ValueError as exc:
            return _response_error(str(exc), 400)

        try:
            with db_connection(app) as connection:
                cursor = connection.cursor(dictionary=True)
                cursor.execute(
                    "SELECT id, name, email, password_hash FROM users WHERE email = %s LIMIT 1",
                    (email,),
                )
                user = cursor.fetchone()
                cursor.close()
        except mysql.connector.Error:
            app.logger.exception("MySQL indisponível durante login")
            return _response_error("Banco de dados indisponível. Tente novamente.", 503)

        if not user or not check_password_hash(user["password_hash"], password):
            return _response_error("E-mail ou senha incorretos.", 401)

        session.clear()
        session.permanent = True
        session["user_id"] = int(user["id"])
        csrf = _make_csrf_token()
        return jsonify({
            "user": {"id": int(user["id"]), "name": user["name"], "email": user["email"]},
            "csrf_token": csrf,
        })

    @app.post("/api/auth/logout")
    def logout():
        session.clear()
        csrf = _make_csrf_token()
        return jsonify({"ok": True, "csrf_token": csrf})

    @app.get("/api/me")
    @_authenticated
    def me():
        try:
            with db_connection(app) as connection:
                cursor = connection.cursor(dictionary=True)
                cursor.execute(
                    "SELECT id, name, email, created_at FROM users WHERE id = %s LIMIT 1",
                    (session["user_id"],),
                )
                user = cursor.fetchone()
                cursor.close()
        except mysql.connector.Error:
            app.logger.exception("MySQL indisponível ao consultar sessão")
            return _response_error("Banco de dados indisponível.", 503)
        if not user:
            session.clear()
            return _response_error("A conta não foi encontrada. Faça login novamente.", 401)
        created_at = user["created_at"].isoformat() if user.get("created_at") else None
        return jsonify({"user": {"id": int(user["id"]), "name": user["name"], "email": user["email"], "created_at": created_at}})

    @app.get("/api/analyses")
    @_authenticated
    def list_analyses():
        try:
            with db_connection(app) as connection:
                cursor = connection.cursor(dictionary=True)
                cursor.execute(
                    "SELECT id, target, result_json, created_at FROM analyses "
                    "WHERE user_id = %s ORDER BY created_at DESC LIMIT 30",
                    (session["user_id"],),
                )
                rows = cursor.fetchall()
                cursor.close()
        except mysql.connector.Error:
            app.logger.exception("MySQL indisponível ao listar análises")
            return _response_error("Não foi possível carregar o histórico agora.", 503)
        items = []
        for row in rows:
            result = _parse_json(row["result_json"])
            items.append({
                "id": int(row["id"]),
                "target": row["target"],
                "title": result.get("title", "Análise salva"),
                "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
            })
        return jsonify({"analyses": items})

    @app.post("/api/analyses")
    @_authenticated
    def create_analysis():
        try:
            data = _json_object()
            target = data.get("target")
            if target not in {"profession", "team"}:
                raise ValueError("Escolha um tipo de análise válido.")
            answers = _validate_answers(data.get("answers"), target)
        except ValueError as exc:
            return _response_error(str(exc), 400)

        result = build_recommendation(target, answers)
        try:
            with db_connection(app) as connection:
                cursor = connection.cursor()
                cursor.execute(
                    "INSERT INTO analyses (user_id, target, answers_json, result_json) "
                    "VALUES (%s, %s, %s, %s)",
                    (
                        session["user_id"],
                        target,
                        json.dumps(answers, ensure_ascii=False, separators=(",", ":")),
                        json.dumps(result, ensure_ascii=False, separators=(",", ":")),
                    ),
                )
                analysis_id = int(cursor.lastrowid)
                connection.commit()
                cursor.close()
        except mysql.connector.Error:
            app.logger.exception("MySQL indisponível ao salvar análise")
            return _response_error("Não foi possível salvar a análise agora.", 503)
        return jsonify({"id": analysis_id, "result": result}), 201

    @app.get("/api/analyses/<int:analysis_id>")
    @_authenticated
    def get_analysis(analysis_id: int):
        try:
            with db_connection(app) as connection:
                cursor = connection.cursor(dictionary=True)
                cursor.execute(
                    "SELECT id, target, answers_json, result_json, created_at FROM analyses "
                    "WHERE id = %s AND user_id = %s LIMIT 1",
                    (analysis_id, session["user_id"]),
                )
                row = cursor.fetchone()
                cursor.close()
        except mysql.connector.Error:
            app.logger.exception("MySQL indisponível ao consultar análise")
            return _response_error("Não foi possível carregar essa análise agora.", 503)
        if not row:
            return _response_error("Análise não encontrada.", 404)
        return jsonify({
            "id": int(row["id"]),
            "target": row["target"],
            "answers": _parse_json(row["answers_json"]),
            "result": _parse_json(row["result_json"]),
            "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
        })

    @app.delete("/api/account")
    @_authenticated
    def delete_account():
        user_id = session["user_id"]
        try:
            with db_connection(app) as connection:
                cursor = connection.cursor()
                cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
                connection.commit()
                cursor.close()
        except mysql.connector.Error:
            app.logger.exception("MySQL indisponível ao excluir conta")
            return _response_error("Não foi possível excluir a conta agora.", 503)
        session.clear()
        csrf = _make_csrf_token()
        return jsonify({"ok": True, "csrf_token": csrf})

    return app


def _validate_answers(raw: Any, target: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("As respostas do questionário não foram enviadas corretamente.")
    answers: dict[str, Any] = {
        "target": target,
        "name": _normalize_text(raw.get("name"), "nome", 120, required=True),
        "city": _normalize_text(raw.get("city"), "cidade", 120, required=True),
        "education": _normalize_text(raw.get("education"), "formação", 240, required=True),
        "superpower": _normalize_text(raw.get("superpower"), "habilidade", 240, required=True),
        "hobby": _normalize_text(raw.get("hobby"), "interesses", 240),
        "animal": _normalize_text(raw.get("animal"), "animal favorito", 60),
        "color": _normalize_text(raw.get("color"), "cor favorita", 60),
    }
    raw_age = raw.get("age")
    if isinstance(raw_age, bool):
        raise ValueError("Informe uma idade numérica entre 13 e 120 anos.")
    try:
        age = int(raw_age)
    except (TypeError, ValueError, OverflowError):
        raise ValueError("Informe uma idade numérica entre 13 e 120 anos.") from None
    if isinstance(raw_age, float) and not raw_age.is_integer():
        raise ValueError("A idade deve ser um número inteiro entre 13 e 120 anos.")
    if isinstance(raw_age, str) and not re.fullmatch(r"\d+", raw_age.strip()):
        raise ValueError("A idade deve ser um número inteiro entre 13 e 120 anos.")
    if not 13 <= age <= 120:
        raise ValueError("A idade deve estar entre 13 e 120 anos.")
    answers["age"] = age

    work_style = raw.get("work_style")
    if work_style not in {"remote", "onsite", "hybrid"}:
        raise ValueError("Escolha uma preferência de trabalho válida.")
    decision_style = raw.get("decision_style")
    if decision_style not in {"analytical", "creative", "collaborative"}:
        raise ValueError("Escolha um estilo de decisão válido.")
    answers["work_style"] = work_style
    answers["decision_style"] = decision_style
    return answers


@contextmanager
def db_connection(app: Flask) -> Iterator[Any]:
    """Borrow a pooled MySQL connection and always return it to the pool."""
    pool = app.extensions.get("mysql_pool")
    if pool is None:
        with _POOL_LOCK:
            pool = app.extensions.get("mysql_pool")
            if pool is None:
                size = int(app.config["MYSQL_POOL_SIZE"])
                if not 1 <= size <= 32:
                    raise RuntimeError("MYSQL_POOL_SIZE deve ficar entre 1 e 32.")
                options: dict[str, Any] = {
                    "host": app.config["MYSQL_HOST"],
                    "port": app.config["MYSQL_PORT"],
                    "user": app.config["MYSQL_USER"],
                    "password": app.config["MYSQL_PASSWORD"],
                    "database": app.config["MYSQL_DATABASE"],
                    "pool_name": f"aether_{secrets.token_hex(4)}",
                    "pool_size": size,
                    "pool_reset_session": True,
                    "connection_timeout": 5,
                    "charset": "utf8mb4",
                }
                ssl_ca = app.config.get("MYSQL_SSL_CA")
                if ssl_ca:
                    options["ssl_ca"] = ssl_ca
                    options["ssl_verify_cert"] = True
                app.extensions["mysql_pool"] = pooling.MySQLConnectionPool(**options)
                pool = app.extensions["mysql_pool"]
    connection = pool.get_connection()
    try:
        yield connection
    finally:
        connection.close()


if __name__ == "__main__":
    # Development convenience only. In Docker/production use the Gunicorn command.
    create_app().run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=False)
