const cards = [document.getElementById('card0'), document.getElementById('card1')];
let currentIndex = 0;
let touchStartX = 0;
let touchEndX = 0;

function handleGesture() {
    if (touchEndX - touchStartX > 50) {
        showNextCard();
    }
}

function showNextCard() {
    const currentCard = cards[currentIndex];
    const nextIndex = (currentIndex + 1) % cards.length;
    const nextCard = cards[nextIndex];

    nextCard.classList.remove('hidden');
    nextCard.setAttribute('aria-hidden', 'false');
    nextCard.style.transform = 'rotateY(90deg)';
    currentCard.classList.add('flipOut');

    setTimeout(() => {
        currentCard.classList.remove('flipOut');
        currentCard.classList.add('hidden');
        currentCard.setAttribute('aria-hidden', 'true');
        currentCard.style.transform = 'rotateY(90deg)';
        nextCard.classList.add('flipIn');

        setTimeout(() => {
            nextCard.classList.remove('flipIn');
            nextCard.style.transform = 'rotateY(0deg)';
            currentIndex = nextIndex;
        }, 600);
    }, 600);
}

document.addEventListener('touchstart', e => {
    touchStartX = e.changedTouches[0].screenX;
});

document.addEventListener('touchend', e => {
    touchEndX = e.changedTouches[0].screenX;
    handleGesture();
});


    
const colors = ['#d94e4e', '#fdd835', '#4fc3f7', '#81c784', '#ba68c8'];
function randomRange(min, max) {
    return Math.random() * (max - min) + min;
}
function createConfetti() {
    const confetti = document.createElement('div');
    confetti.classList.add('confetti');
    confetti.style.left = Math.random() * window.innerWidth + 'px';
    confetti.style.width = confetti.style.height = randomRange(8, 14) + 'px';
    confetti.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
    confetti.style.animationDuration = randomRange(3, 6) + 's';
    confetti.style.animationDelay = (-randomRange(0, 6)) + 's';
    document.body.appendChild(confetti);
    setTimeout(() => {
        confetti.remove();
    }, 6000);
}
setInterval(() => {
    for(let i = 0; i < 5; i++) {
        createConfetti();
    }
}, 500);

function randomRange(min, max) {
    return Math.random() * (max - min) + min;
}

    
function createBalloon(delay, left, color1, color2) {
    const balloon = document.createElement('div');
    balloon.classList.add('balloon');
    balloon.style.left = left + 'vw';
    balloon.style.background = `radial-gradient(circle at 30% 30%, ${color1}, ${color2})`;
    balloon.style.animationDuration = (randomRange(8, 12)) + 's';
    balloon.style.animationDelay = delay + 's';
    document.body.appendChild(balloon);
}

createBalloon(0, 20, '#f8b500', '#d47500');
createBalloon(2, 40, '#d47500', '#f8b500');
createBalloon(4, 50, '#fceabb', '#f8b500');
createBalloon(6, 80, '#d47500', '#fceabb');
createBalloon(1, 10, '#f8b500', '#fceabb');
createBalloon(3, 70, '#fceabb', '#d47500');
