document.addEventListener('DOMContentLoaded', () => {
    const terminalForm = document.getElementById('terminal-form');
    const commandInput = document.getElementById('command-input');
    const quickLoadBtn = document.getElementById('quick-load-btn');
    const loadingScreen = document.getElementById('loading-screen');
    const terminalOutput = document.querySelector('.terminal-output');

    let isQuickLoadEnabled = localStorage.getItem('quickLoad') === 'true';

    function updateQuickLoadButton() {
        if (isQuickLoadEnabled) {
            quickLoadBtn.textContent = 'Быстрая загрузка: ВКЛ';
            quickLoadBtn.style.borderColor = 'var(--main-text)';
            quickLoadBtn.style.boxShadow = '0 0 5px var(--main-text)';
        } else {
            quickLoadBtn.textContent = 'Быстрая загрузка: ВЫКЛ';
            quickLoadBtn.style.borderColor = 'var(--border-color)';
            quickLoadBtn.style.boxShadow = 'none';
        }
    }

    quickLoadBtn.addEventListener('click', () => {
        isQuickLoadEnabled = !isQuickLoadEnabled;
        localStorage.setItem('quickLoad', isQuickLoadEnabled);
        updateQuickLoadButton();
    });


    async function sha256(message) {
        const msgBuffer = new TextEncoder().encode(message);
        const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
        return hashHex;
    }

    function addTerminalLine(text, originalCommand) {
        const line = document.createElement('p');
        line.innerText = `> ${originalCommand}\n${text}`;
        terminalOutput.insertBefore(line, terminalForm);
        commandInput.value = '';
        terminalOutput.scrollTop = terminalOutput.scrollHeight;
    }

    terminalForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const originalCommand = commandInput.value.trim();
        const command = originalCommand.toLowerCase();

        const loginHash = '428821350e9691491f616b754cd8315fb86d797ab35d843479e732ef90665324';
        const connectHash = '5a638a128ca67348f1073ba0aed26d85905a29128cbd71b250c9cf4e598c7f0d';

        const commandHash = await sha256(command);

        if (commandHash === loginHash || commandHash === connectHash) {
            if (isQuickLoadEnabled) {
                window.location.href = 'dashboard/';
            } else {
                const progressBar = document.querySelector('.loading-bar-progress');
                loadingScreen.style.display = 'flex';
                setTimeout(() => {
                    if (progressBar) {
                        progressBar.style.width = '100%';
                    }
                }, 100);
                setTimeout(() => {
                    window.location.href = 'dashboard/';
                }, 2500);
            }
        } else {
            let responseText;
            switch (command) {
                case 'ls':
                case 'dir':
                    responseText = 'Пх... Смешно. Но это не терминал с директориями.';
                    break;
                case 'help':
                case '?':
                    responseText = '[ОШИБКА] Система не предоставляет справок. Протокол доступа: S.H.A. 256.';
                    break;
                case 'whoami':
                    responseText = 'Ты тот, кто не должен здесь быть.';
                    break;
                case 'sudo':
                case 'su':
                    responseText = '[ОШИБКА] Отказано в доступе. У вас нет таких прав.';
                    break;
                case 'exit':
                case 'quit':
                    responseText = 'Отсюда нет выхода.';
                    break;
                case 'clear':
                case 'cls':
                    responseText = 'Прошлое не стереть.';
                    break;
                default:
                    responseText = '[ОШИБКА] Неверная команда или протокол доступа.';
                    break;
            }
            addTerminalLine(responseText, originalCommand);
        }
    });


    updateQuickLoadButton();
});
