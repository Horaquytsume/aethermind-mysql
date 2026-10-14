(() => {
  'use strict';

  const viewIds = ['authView', 'dashboardView', 'assessmentView', 'processingView', 'resultsView'];
  const state = {
    user: null,
    csrfToken: null,
    authMode: 'login',
    step: 0,
    answers: {},
  };

  const questions = [
    {
      key: 'target',
      title: 'O que você quer explorar?',
      sub: 'Escolha entre uma orientação profissional ou um perfil recreativo de torcida.',
      options: [
        { text: '💼 Áreas profissionais e equipe de apoio', value: 'profession' },
        { text: '⚽ Perfil de torcida (recreativo)', value: 'team' },
      ],
    },
    { key: 'name', title: 'Como podemos chamar você?', sub: 'Seu nome será salvo junto desta análise.', custom: true, maxLength: 120, required: true },
    { key: 'age', title: 'Qual é a sua idade?', sub: 'Informe um número entre 13 e 120.', custom: true, inputType: 'number', min: 13, max: 120, required: true },
    { key: 'city', title: 'Onde você mora?', sub: 'Cidade ou estado; usamos apenas para contextualizar sua resposta.', custom: true, maxLength: 120, required: true, placeholder: 'Ex.: São Paulo - SP' },
    { key: 'education', title: 'Qual é sua formação ou nível de estudos?', sub: 'Inclua cursos ou áreas que está aprendendo, se quiser.', custom: true, maxLength: 240, required: true, placeholder: 'Ex.: Ensino médio, Mecatrônica, curso de Python...' },
    {
      key: 'work_style',
      title: 'Como você prefere trabalhar?',
      sub: 'Escolha a rotina que mais combina com você.',
      options: [
        { text: '🏠 Autonomia e trabalho remoto', value: 'remote' },
        { text: '🏢 Interação presencial', value: 'onsite' },
        { text: '⚡ Híbrido, com foco em entregas', value: 'hybrid' },
      ],
    },
    {
      key: 'decision_style',
      title: 'Como você costuma decidir?',
      sub: 'Não existe resposta certa ou errada.',
      options: [
        { text: '📊 Análise, dados e lógica', value: 'analytical' },
        { text: '💡 Criatividade e rapidez', value: 'creative' },
        { text: '🤝 Conversa, colaboração e empatia', value: 'collaborative' },
      ],
    },
    { key: 'superpower', title: 'Qual habilidade as pessoas mais elogiam em você?', sub: 'Uma habilidade que gostaria de usar mais no trabalho.', custom: true, maxLength: 240, required: true, placeholder: 'Ex.: organização, resolver problemas, comunicação...' },
    { key: 'hobby', title: 'Quais interesses ou hobbies você gostaria de compartilhar?', sub: 'Esta resposta é opcional e pode ajudar a contextualizar os resultados.', custom: true, maxLength: 240, required: false, placeholder: 'Ex.: jogos, carros, leitura, programação...' },
    { key: 'animal', title: 'Qual é seu animal favorito?', sub: 'Pergunta opcional, apenas para deixar a experiência mais pessoal.', custom: true, maxLength: 60, required: false, placeholder: 'Ex.: gato, cachorro, lobo...' },
    { key: 'color', title: 'Qual é sua cor favorita?', sub: 'Pergunta opcional.', custom: true, maxLength: 60, required: false, placeholder: 'Ex.: azul, roxo, verde...' },
  ];

  const $ = (selector) => document.querySelector(selector);
  const appNotice = $('#appNotice');
  const authForm = $('#authForm');
  const authEmail = $('#authEmail');
  const authPass = $('#authPass');
  const regName = $('#regName');
  const authError = $('#authError');
  const authSubmitBtn = $('#authSubmitBtn');
  const nameFieldContainer = $('#nameFieldContainer');
  const consentContainer = $('#consentContainer');
  const regConsent = $('#regConsent');
  const customInput = $('#customAnswerInput');
  const customInputContainer = $('#customInputContainer');
  const questionOptions = $('#questionOptions');
  const modal = $('#customModal');
  const resultsContainer = $('#resultsContainer');

  const questionNav = document.createElement('div');
  questionNav.className = 'flex items-center justify-between gap-3 pt-2';
  questionNav.innerHTML = '';
  const backButton = document.createElement('button');
  backButton.type = 'button';
  backButton.dataset.action = 'question-back';
  backButton.className = 'hidden px-4 py-3 bg-slate-800 hover:bg-slate-700 text-slate-200 font-bold rounded-xl text-xs transition-all border border-slate-700';
  backButton.textContent = '← Voltar';
  const skipButton = document.createElement('button');
  skipButton.type = 'button';
  skipButton.dataset.action = 'skip-answer';
  skipButton.className = 'hidden px-4 py-3 bg-slate-800 hover:bg-slate-700 text-slate-200 font-bold rounded-xl text-xs transition-all border border-slate-700';
  skipButton.textContent = 'Pular pergunta';
  questionNav.append(backButton, skipButton);
  customInputContainer.parentElement.after(questionNav);

  function notify(text) {
    appNotice.textContent = text;
  }

  function showView(viewId) {
    viewIds.forEach((id) => {
      const element = document.getElementById(id);
      if (element) element.classList.toggle('hidden', id !== viewId);
    });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function setAuthError(text = '') {
    authError.textContent = text;
    authError.classList.toggle('hidden', !text);
    if (text) notify(text);
  }

  function showModal(title, message, icon = '⚠️') {
    $('#modalTitle').textContent = title;
    $('#modalMessage').textContent = message;
    $('#modalIcon').textContent = icon;
    modal.classList.remove('hidden');
    modal.setAttribute('role', 'dialog');
    modal.setAttribute('aria-modal', 'true');
    $('#modalTitle').focus?.();
  }

  function closeModal() {
    modal.classList.add('hidden');
    modal.removeAttribute('role');
    modal.removeAttribute('aria-modal');
  }

  async function refreshCsrfToken() {
    const response = await fetch('/api/auth/csrf', {
      method: 'GET',
      credentials: 'same-origin',
      cache: 'no-store',
      headers: { Accept: 'application/json' },
    });
    const data = await response.json();
    if (!response.ok || !data.csrf_token) throw new Error('Não foi possível iniciar a sessão segura.');
    state.csrfToken = data.csrf_token;
  }

  async function api(path, options = {}, retry = true) {
    const method = (options.method || 'GET').toUpperCase();
    if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method) && !state.csrfToken) {
      await refreshCsrfToken();
    }
    const headers = new Headers(options.headers || {});
    headers.set('Accept', 'application/json');
    if (options.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
    if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) headers.set('X-CSRF-Token', state.csrfToken);

    let response;
    try {
      response = await fetch(path, { ...options, method, headers, credentials: 'same-origin', cache: 'no-store' });
    } catch {
      throw new Error('Sem conexão com o servidor. Confira se o app e o MySQL estão iniciados.');
    }
    const data = await response.json().catch(() => ({}));
    if (response.status === 403 && retry && ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
      await refreshCsrfToken();
      return api(path, options, false);
    }
    if (!response.ok) {
      const error = new Error(data.error || 'Não foi possível concluir a solicitação.');
      error.status = response.status;
      throw error;
    }
    return data;
  }

  function setAuthMode(mode) {
    state.authMode = mode === 'register' ? 'register' : 'login';
    const registering = state.authMode === 'register';
    nameFieldContainer.classList.toggle('hidden', !registering);
    consentContainer.classList.toggle('hidden', !registering);
    regName.required = registering;
    regConsent.required = registering;
    authPass.autocomplete = registering ? 'new-password' : 'current-password';
    authPass.minLength = registering ? 12 : 1;
    authPass.placeholder = registering ? 'Mínimo de 12 caracteres' : 'Digite sua senha';
    authPass.previousElementSibling.textContent = registering ? 'Senha (mínimo de 12 caracteres)' : 'Senha';
    authSubmitBtn.textContent = registering ? 'Criar conta' : 'Entrar no Sistema';
    $('#tabLogin').classList.toggle('text-cyan-400', !registering);
    $('#tabLogin').classList.toggle('font-bold', !registering);
    $('#tabLogin').classList.toggle('border-cyan-400', !registering);
    $('#tabLogin').classList.toggle('text-slate-400', registering);
    $('#tabLogin').classList.toggle('border-transparent', registering);
    $('#tabRegister').classList.toggle('text-cyan-400', registering);
    $('#tabRegister').classList.toggle('font-bold', registering);
    $('#tabRegister').classList.toggle('border-cyan-400', registering);
    $('#tabRegister').classList.toggle('text-slate-400', !registering);
    $('#tabRegister').classList.toggle('border-transparent', !registering);
    setAuthError('');
  }

  function updateUser(user) {
    state.user = user;
    $('#welcomeName').textContent = user.name;
    const initials = user.name.trim().split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase();
    $('#userAvatar').textContent = initials || 'AM';
  }

  async function showDashboard(user) {
    updateUser(user);
    showView('dashboardView');
    await loadHistory();
  }

  async function loadHistory() {
    const historyList = $('#historyList');
    historyList.replaceChildren();
    try {
      const data = await api('/api/analyses');
      if (!data.analyses.length) {
        const empty = document.createElement('p');
        empty.className = 'text-xs text-slate-400';
        empty.textContent = 'Suas análises salvas aparecerão aqui.';
        historyList.append(empty);
        return;
      }
      for (const item of data.analyses) {
        const button = document.createElement('button');
        button.type = 'button';
        button.dataset.action = 'open-analysis';
        button.dataset.analysisId = String(item.id);
        button.className = 'w-full text-left p-3 rounded-xl bg-slate-900/70 border border-slate-800 hover:border-cyan-700 transition-colors';
        const title = document.createElement('span');
        title.className = 'block text-xs font-bold text-slate-200';
        title.textContent = item.title;
        const date = document.createElement('span');
        date.className = 'block mt-1 text-[10px] text-slate-500';
        date.textContent = formatDate(item.created_at);
        button.append(title, date);
        historyList.append(button);
      }
    } catch (error) {
      const message = document.createElement('p');
      message.className = 'text-xs text-amber-300';
      message.textContent = error.message;
      historyList.append(message);
    }
  }

  function formatDate(value) {
    if (!value) return 'Data indisponível';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return 'Data indisponível';
    return new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' }).format(date);
  }

  async function handleAuth(event) {
    event.preventDefault();
    setAuthError('');
    authSubmitBtn.disabled = true;
    authSubmitBtn.classList.add('opacity-60', 'cursor-wait');
    try {
      const registering = state.authMode === 'register';
      const payload = {
        email: authEmail.value.trim(),
        password: authPass.value,
      };
      if (registering) {
        payload.name = regName.value.trim();
        payload.consent = regConsent.checked;
      }
      const data = await api(registering ? '/api/auth/register' : '/api/auth/login', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      state.csrfToken = data.csrf_token;
      authPass.value = '';
      if (regConsent) regConsent.checked = false;
      await showDashboard(data.user);
    } catch (error) {
      setAuthError(error.message);
    } finally {
      authSubmitBtn.disabled = false;
      authSubmitBtn.classList.remove('opacity-60', 'cursor-wait');
    }
  }

  async function logout() {
    try {
      const data = await api('/api/auth/logout', { method: 'POST', body: '{}' });
      state.csrfToken = data.csrf_token;
    } catch (error) {
      showModal('Não foi possível encerrar', error.message);
      return;
    }
    state.user = null;
    authForm.reset();
    setAuthMode('login');
    showView('authView');
    notify('Sessão encerrada.');
  }

  function startAssessment() {
    if (!state.user) {
      showView('authView');
      return;
    }
    state.step = 0;
    state.answers = { name: state.user.name };
    showView('assessmentView');
    renderQuestion();
  }

  function renderQuestion() {
    const question = questions[state.step];
    if (!question) return submitAssessment();
    $('#stepIndicator').textContent = `Etapa ${state.step + 1} de ${questions.length}`;
    $('#questionTitle').textContent = question.title;
    $('#questionSub').textContent = question.sub;
    questionOptions.replaceChildren();
    customInputContainer.classList.toggle('hidden', !question.custom);
    skipButton.classList.toggle('hidden', !question.custom || question.required);
    backButton.classList.toggle('hidden', state.step === 0);

    if (question.custom) {
      customInput.type = question.inputType || 'text';
      customInput.value = state.answers[question.key] ?? '';
      customInput.placeholder = question.placeholder || 'Digite sua resposta';
      customInput.maxLength = question.maxLength || 240;
      customInput.required = Boolean(question.required);
      customInput.removeAttribute('min');
      customInput.removeAttribute('max');
      if (question.inputType === 'number') {
        customInput.min = String(question.min || 13);
        customInput.max = String(question.max || 120);
        customInput.step = '1';
      } else {
        customInput.removeAttribute('step');
      }
      window.setTimeout(() => customInput.focus(), 0);
      return;
    }

    for (const option of question.options) {
      const button = document.createElement('button');
      button.type = 'button';
      button.dataset.action = 'choose-option';
      button.dataset.value = option.value;
      button.className = 'w-full text-left p-4 rounded-2xl bg-slate-900/70 border border-slate-700 hover:border-cyan-500 hover:bg-cyan-950/30 text-slate-200 font-semibold text-sm transition-all';
      button.textContent = option.text;
      questionOptions.append(button);
    }
  }

  function continueQuestion(value) {
    const question = questions[state.step];
    state.answers[question.key] = value;
    state.step += 1;
    renderQuestion();
  }

  function submitCustomAnswer() {
    const question = questions[state.step];
    const value = customInput.value.trim();
    if (question.required && !value) {
      customInput.focus();
      showModal('Resposta necessária', 'Preencha essa resposta para continuar.');
      return;
    }
    if (question.inputType === 'number' && value && (!Number.isInteger(Number(value)) || Number(value) < 13 || Number(value) > 120)) {
      customInput.focus();
      showModal('Confira a idade', 'Informe um número inteiro entre 13 e 120.');
      return;
    }
    if (value.length > (question.maxLength || 240)) {
      showModal('Resposta muito longa', 'Reduza o texto e tente novamente.');
      return;
    }
    continueQuestion(value);
  }

  function previousQuestion() {
    if (state.step > 0) {
      state.step -= 1;
      renderQuestion();
    }
  }

  function skipQuestion() {
    const question = questions[state.step];
    if (question.required) return;
    continueQuestion('');
  }

  async function submitAssessment() {
    showView('processingView');
    $('#processingStepText').textContent = 'Validando respostas e aplicando critérios transparentes...';
    try {
      const { target, ...answers } = state.answers;
      const data = await api('/api/analyses', {
        method: 'POST',
        body: JSON.stringify({ target, answers }),
      });
      renderResult(data.result);
    } catch (error) {
      showModal('Não foi possível salvar', error.message);
      showView('assessmentView');
    }
  }

  function addTextSection(parent, title, values) {
    if (!Array.isArray(values) || !values.length) return;
    const section = document.createElement('section');
    section.className = 'glass-panel p-6 rounded-3xl';
    const heading = document.createElement('h3');
    heading.className = 'text-lg font-bold text-white mb-3';
    heading.textContent = title;
    const list = document.createElement('ul');
    list.className = 'space-y-2';
    values.forEach((value) => {
      const item = document.createElement('li');
      item.className = 'text-sm text-slate-300 leading-relaxed';
      item.textContent = `• ${value}`;
      list.append(item);
    });
    section.append(heading, list);
    parent.append(section);
  }

  function renderResult(result) {
    resultsContainer.replaceChildren();
    const primary = document.createElement('section');
    primary.className = 'md:col-span-2 glass-panel p-7 sm:p-8 rounded-3xl border border-cyan-700/40';
    const title = document.createElement('h3');
    title.className = 'text-xl sm:text-2xl font-extrabold text-white';
    title.textContent = result.title || 'Sua sugestão inicial';
    const summary = document.createElement('p');
    summary.className = 'mt-3 text-sm text-slate-300 leading-relaxed';
    summary.textContent = result.summary || '';
    const notice = document.createElement('p');
    notice.className = 'mt-4 p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs text-amber-200 leading-relaxed';
    notice.textContent = result.notice || 'Orientação inicial; confira outras fontes antes de tomar decisões.';
    primary.append(title, summary, notice);
    resultsContainer.append(primary);

    addTextSection(resultsContainer, result.kind === 'team' ? 'Ideias para explorar' : 'Áreas para investigar', result.kind === 'team' ? result.suggestions : result.roles);
    if (Array.isArray(result.squad)) {
      const squadValues = result.squad.map((member) => `${member.role}: ${member.description}`);
      addTextSection(resultsContainer, 'Papéis sugeridos para seu SQUAD de apoio', squadValues);
    }
    addTextSection(resultsContainer, 'O que pesou nesta sugestão', result.basis);
    showView('resultsView');
    notify('Análise calculada e salva no MySQL.');
  }

  async function openSavedAnalysis(id) {
    if (!Number.isInteger(id) || id < 1) return;
    try {
      const data = await api(`/api/analyses/${id}`);
      renderResult(data.result);
    } catch (error) {
      showModal('Histórico indisponível', error.message);
    }
  }

  async function deleteAccount() {
    const confirmed = window.confirm('Excluir sua conta e todas as análises salvas? Esta ação não pode ser desfeita.');
    if (!confirmed) return;
    try {
      const data = await api('/api/account', { method: 'DELETE' });
      state.csrfToken = data.csrf_token;
      state.user = null;
      state.answers = {};
      authForm.reset();
      setAuthMode('login');
      showView('authView');
      showModal('Conta excluída', 'Sua conta e as análises associadas foram removidas do banco de dados.', '✅');
    } catch (error) {
      showModal('Não foi possível excluir', error.message);
    }
  }

  document.addEventListener('click', (event) => {
    const option = event.target.closest('[data-action="choose-option"]');
    if (option) {
      const question = questions[state.step];
      continueQuestion(option.dataset.value);
      return;
    }
    const button = event.target.closest('[data-action]');
    if (!button) return;
    switch (button.dataset.action) {
      case 'auth-mode': setAuthMode(button.dataset.mode); break;
      case 'logout': logout(); break;
      case 'start-assessment': startAssessment(); break;
      case 'custom-answer': submitCustomAnswer(); break;
      case 'dashboard': showDashboard(state.user); break;
      case 'close-modal': closeModal(); break;
      case 'question-back': previousQuestion(); break;
      case 'skip-answer': skipQuestion(); break;
      case 'delete-account': deleteAccount(); break;
      case 'open-analysis': openSavedAnalysis(Number(button.dataset.analysisId)); break;
      default: break;
    }
  });

  authForm.addEventListener('submit', handleAuth);
  modal.addEventListener('click', (event) => {
    if (event.target === modal) closeModal();
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && !modal.classList.contains('hidden')) closeModal();
  });

  async function boot() {
    setAuthMode('login');
    try {
      await refreshCsrfToken();
      const data = await api('/api/me');
      await showDashboard(data.user);
    } catch (error) {
      state.user = null;
      showView('authView');
      if (error.status === 503) setAuthError(error.message);
    }
  }

  boot();
})();
