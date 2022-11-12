document.addEventListener("DOMContentLoaded", function() {
    // Scroll today's table to current time column

    var scrollEl = document.querySelector("th.cell_past ~ th:not(.cell_past)");

    if (!scrollEl) { return; }

    var scrollElWrapper = scrollEl.closest(".table-container");
    scrollElWrapper.scroll({
        left: scrollEl.offsetLeft - scrollElWrapper.offsetWidth / 2,
        behavior: 'smooth'
    });
});

document.addEventListener("DOMContentLoaded", function() {
    // Location form utilities

    var locationForm = document.getElementById("location-form");
    var locationSubmit = locationForm.querySelector("button[type='submit']");
    var locationReset = locationForm.querySelector("#location-reset");
    var locationInput = locationForm.querySelector("#location-input");
    var locationsList = locationForm.querySelector("#locations-list");

    locationReset.addEventListener("click", (e) => {
        locationInput.value = "";
        locationInput.focus();
    });

    locationInput.addEventListener("input", (event) => {
        const value = event.target.value;

        locationForm.querySelector("input[type='hidden'][name='latitude']").value = "";
        locationForm.querySelector("input[type='hidden'][name='longitude']").value = "";
        locationSubmit?.setAttribute("disabled", true);

        if(event.inputType == "insertReplacementText" || event.inputType == null) {
            const options = [...locationsList.options];

            const selected_option = options.find(o => o.value === value);

            locationForm.querySelector("input[type='hidden'][name='latitude']").value = selected_option.dataset.latitude
            locationForm.querySelector("input[type='hidden'][name='longitude']").value = selected_option.dataset.longitude
            locationSubmit?.removeAttribute("disabled");
        }
    });

    locationInput.addEventListener("input", (e) => {
        if (!window.fetch) return;

        window.fetch("/location?search=" + e.target.value)
        .then(function (r) { return r.json() })
        .then(function(data) {
            locationsList.innerHTML = "";
            if (!data?.results || data.results.length < 1) return;

            const optionsContainer = document.createDocumentFragment();

            data.results.forEach(loc => {
                const name = `${loc.name}, ${loc?.admin1 || loc.admin2} (${loc.country})`;
                const opt_element = optionsContainer.appendChild(document.createElement("option"));

                opt_element.value = name;
                opt_element.dataset.latitude = loc.latitude;
                opt_element.dataset.longitude = loc.longitude;
            })

            locationsList.appendChild(optionsContainer);
        });
    });
});

// Freely adapted from https://codepen.io/Vijit_Ail/pen/pmbypw

const pStart = { x: 0, y: 0 };
const pCurrent = { x: 0, y: 0 };
const main = document.querySelector("main");

function loading() {
    main.classList.add('is-loading');

    setTimeout(() => {
        window.location.reload();
    }, 500);
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
