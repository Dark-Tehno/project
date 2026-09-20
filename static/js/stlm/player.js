(() => {
    const players = document.querySelectorAll('[data-audio-player]');

    const formatTime = (seconds) => {
        if (!Number.isFinite(seconds)) return '0:00';
        const minutes = Math.floor(seconds / 60);
        const remainder = Math.floor(seconds % 60).toString().padStart(2, '0');
        return `${minutes}:${remainder}`;
    };

    players.forEach((player) => {
        const audio = player.querySelector('.hb-audio');
        const toggle = player.querySelector('[data-player-toggle]');
        const progress = player.querySelector('[data-player-progress]');
        const volume = player.querySelector('[data-player-volume]');
        const current = player.querySelector('[data-player-current]');
        const durationEl = player.querySelector('[data-player-duration]');
        const status = player.querySelector('[data-player-status]');

        let isSeeking = false;

        // Обновление прогресс-бара во время обычного проигрывания
        const updateProgress = () => {
            // Принудительно завершаем поиск, если трек закончился сам
            if (audio.currentTime >= audio.duration && isSeeking) {
                finishSeeking();
            }

            if (isSeeking) return;

            const percent = audio.duration ? (audio.currentTime / audio.duration) * 100 : 0;
            progress.value = percent;
            current.textContent = formatTime(audio.currentTime);
        };

        const updateButton = () => {
            const isPlaying = !audio.paused;
            toggle.textContent = isPlaying ? '❚❚' : '▶';
            toggle.setAttribute('aria-label', isPlaying ? 'Поставить на паузу' : 'Воспроизвести трек');
            status.textContent = isPlaying ? 'Воспроизводится' : 'Пауза';
        };

        toggle.addEventListener('click', () => {
            if (audio.paused) {
                audio.play().catch(err => console.error('Ошибка автовоспроизведения:', err));
            } else {
                audio.pause();
            }
        });

        const startSeeking = () => {
            if (!Number.isFinite(audio.duration) || audio.duration <= 0) return;
            isSeeking = true;
            progress.focus(); 
        };

        const seek = () => {
            if (!Number.isFinite(audio.duration) || audio.duration <= 0) return;

            const value = Number(progress.value);
            const nextTime = (value / 100) * audio.duration;

            try {
                audio.currentTime = nextTime;
                current.textContent = formatTime(nextTime);
            } catch (e) {
                console.error('Не удалось установить текущее время:', e);
            }
        };

        const finishSeeking = () => {
            if (!isSeeking) return;
            seek();
            isSeeking = false;
            updateProgress();
        };

        progress.addEventListener('pointerdown', startSeeking);

        progress.addEventListener('input', (e) => {
            const tempPercent = Number(e.target.value);
            seek();
            current.textContent = formatTime((tempPercent / 100) * audio.duration);
        });

        ['pointerup', 'pointercancel', 'lostpointercapture', 'change'].forEach(evt => {
            progress.addEventListener(evt, finishSeeking);
        });

        volume.addEventListener('input', () => {
            audio.volume = Number(volume.value);
        });

        audio.addEventListener('loadedmetadata', () => {
            durationEl.textContent = formatTime(audio.duration);
            progress.value = 0;
            updateProgress();
        });

        audio.addEventListener('durationchange', () => {
            if (progress && Number.isFinite(audio.duration)) {
                progress.max = 100;
            }
        });

        audio.addEventListener('timeupdate', updateProgress);
        audio.addEventListener('play', updateButton);
        audio.addEventListener('pause', updateButton);

        audio.addEventListener('ended', () => {
            updateButton();
            status.textContent = 'Трек завершён';
            progress.value = 100;
            current.textContent = formatTime(audio.duration);
            isSeeking = false; // Страховка
        });

        audio.addEventListener('error', (e) => {
            console.error('Ошибка аудио:', e);
            status.textContent = 'Ошибка загрузки';
        });
    });
})();