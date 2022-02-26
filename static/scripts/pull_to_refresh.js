// Freely adapted from https://codepen.io/Vijit_Ail/pen/pmbypw

const pStart = { x: 0, y: 0 };
const pCurrent = { x: 0, y: 0 };
const main = document.querySelector("main");

function loading() {
    main.classList.add('is-loading');
    window.location.reload();
}

function swipeStart(e) {
    if (window.scrollY > 0) return;

    if (typeof e["targetTouches"] !== "undefined") {
        let touch = e.targetTouches[0];
        pStart.x = touch.screenX;
        pStart.y = touch.screenY;
    } else {
        pStart.x = e.screenX;
        pStart.y = e.screenY;
    }
}

function swipe(e) {
    if (window.scrollY > 0) return;

    if (typeof e["changedTouches"] !== "undefined") {
        let touch = e.changedTouches[0];
        pCurrent.x = touch.screenX;
        pCurrent.y = touch.screenY;
    } else {
        pCurrent.x = e.screenX;
        pCurrent.y = e.screenY;
    }

    const changeY = pStart.y < pCurrent.y ? Math.abs(pStart.y - pCurrent.y) : 0;

    if (changeY > 100) {
        loading();
    }
}

document.addEventListener("touchstart", e => swipeStart(e), false);
document.addEventListener("touchmove", e => swipe(e), false);
