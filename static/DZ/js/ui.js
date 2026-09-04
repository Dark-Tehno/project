document.addEventListener('DOMContentLoaded', () => {
    const stabilizeBtn = document.getElementById('stabilize-btn');
    const body = document.body;

    if (localStorage.getItem('isStabilized') === 'true') {
        body.classList.add('stabilized');
    }

    stabilizeBtn.addEventListener('click', () => {
        body.classList.toggle('stabilized');

        const isStabilized = body.classList.contains('stabilized');
        localStorage.setItem('isStabilized', isStabilized);
    });
});