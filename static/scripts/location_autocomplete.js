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
