document.getElementById('start-menu').addEventListener('click', () => {
    const window = document.getElementById('window');
    window.classList.toggle('hidden');
});

document.getElementById('close-window').addEventListener('click', () => {
    const window = document.getElementById('window');
    window.classList.add('hidden');
});

function updateClock() {
    const now = new Date();
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    document.getElementById('clock').textContent = `${hours}:${minutes}`;
}

setInterval(updateClock, 1000);
updateClock();
