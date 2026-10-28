const menuButton = document.querySelector('.menu-toggle');
const navigation = document.querySelector('.main-nav');
const eventsMenu = document.querySelector('.nav-events');
if (menuButton && navigation) {
  const closeMenu = () => {
    menuButton.setAttribute('aria-expanded', 'false');
    navigation.classList.remove('is-open');
    if (eventsMenu) eventsMenu.open = false;
  };
  menuButton.addEventListener('click', () => {
    const open = menuButton.getAttribute('aria-expanded') !== 'true';
    menuButton.setAttribute('aria-expanded', String(open));
    navigation.classList.toggle('is-open', open);
  });
  navigation.addEventListener('click', event => { if (event.target.closest('a')) closeMenu(); });
  document.addEventListener('keydown', event => {
    if (event.key !== 'Escape') return;
    if (eventsMenu?.open) {
      eventsMenu.open = false;
      eventsMenu.querySelector('summary').focus();
    } else if (navigation.classList.contains('is-open')) {
      closeMenu();
      menuButton.focus();
    }
  });
}
if (eventsMenu) {
  document.addEventListener('click', event => {
    if (!eventsMenu.contains(event.target)) eventsMenu.open = false;
  });
  eventsMenu.addEventListener('focusout', event => {
    if (!eventsMenu.contains(event.relatedTarget)) eventsMenu.open = false;
  });
}
const demoButton = document.querySelector('[data-run-demo]');
if (demoButton) demoButton.addEventListener('click', () => {
  const output = document.querySelector('[data-demo-output]');
  output.textContent = "› Hello from GIC!\n› Southeast Asia";
  output.classList.add('has-run');
  demoButton.textContent = '↻ Run again';
});
document.querySelectorAll('[data-auth-mode]').forEach(button => {
  button.addEventListener('click', () => {
    const mode = button.dataset.authMode;
    document.querySelectorAll('[data-auth-panel]').forEach(panel => { panel.hidden = panel.dataset.authPanel !== mode; });
    document.querySelectorAll('[data-auth-mode]').forEach(tab => { tab.setAttribute('aria-pressed', String(tab.dataset.authMode === mode)); });
  });
});
const upload = document.querySelector('#code-file');
if (upload) upload.addEventListener('change', () => {
  const label = document.querySelector('[data-file-label]');
  label.textContent = upload.files.length ? upload.files[0].name : 'Choose your Python file';
});
document.querySelectorAll('[data-submit-form]').forEach(form => {
  form.addEventListener('submit', () => {
    const button = form.querySelector('button[type="submit"]');
    button.disabled = true;
    button.textContent = 'Checking your code…';
  });
});

document.querySelectorAll('[data-answer-check]').forEach(form => {
  const button = form.querySelector('button[type="submit"]');
  const feedback = form.querySelector('[data-answer-feedback]');
  const inputs = [...form.querySelectorAll('textarea')];
  const partFeedback = [...form.querySelectorAll('[data-answer-field-feedback]')];
  let revision = 0;
  form.addEventListener('input', () => {
    revision += 1;
    feedback.textContent = '';
    feedback.className = 'answer-feedback';
    partFeedback.forEach(item => { item.textContent = ''; });
    inputs.forEach(input => input.removeAttribute('aria-invalid'));
  });
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (button.disabled) return;
    const submittedRevision = revision;
    button.disabled = true;
    button.textContent = 'Checking…';
    feedback.textContent = 'Checking your answer…';
    feedback.className = 'answer-feedback';
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch(form.action, {
        method: 'POST', body: new FormData(form),
        headers: { Accept: 'application/json' }, signal: controller.signal,
      });
      if (submittedRevision !== revision) return;
      if (!response.headers.get('content-type')?.includes('application/json')) {
        throw new Error(response.status === 400
          ? 'Your session expired. Reload the page and try again.'
          : 'Unable to check right now. Your answer is still here; please try again.');
      }
      const result = await response.json();
      if (!['correct', 'incorrect', 'invalid', 'unavailable'].includes(result.status)) {
        throw new Error('Unable to check right now. Please try again.');
      }
      if (submittedRevision !== revision) return;
      feedback.textContent = result.message;
      feedback.className = `answer-feedback is-${result.status}`;
      inputs.forEach((input, index) => {
        const correct = result.fields[index];
        partFeedback[index].textContent = correct === undefined ? ''
          : correct ? 'Correct' : 'Not quite — try this part again.';
        if (correct === false) input.setAttribute('aria-invalid', 'true');
        else input.removeAttribute('aria-invalid');
      });
    } catch (error) {
      if (submittedRevision !== revision) return;
      feedback.textContent = error.name === 'AbortError'
        ? 'The check timed out. Your answer is still here; please try again.'
        : error instanceof TypeError
          ? 'Connection lost. Your answer is still here; please try again.' : error.message;
      feedback.className = 'answer-feedback is-invalid';
    } finally {
      clearTimeout(timeout);
      button.disabled = false;
      button.textContent = 'Check answer →';
    }
  });
});
