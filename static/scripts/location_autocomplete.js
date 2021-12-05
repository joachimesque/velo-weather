document.addEventListener("DOMContentLoaded", function() {
    // Location form utilities

    var locationInput = document.getElementById("location-input");
    var locationsList = document.getElementById("locations-list");
    locationInput.onfocus = function (e) {
        e.target.value = "";
    }
    locationInput.onchange = function () {
        document.getElementById("location-form").submit();
        locationInput.disabled = true;
    }
    locationInput.oninput = function (e) {
        if (!window.fetch) return;
        window.fetch("https://geo.api.gouv.fr/communes?nom=" + e.target.value + "&boost=population&limit=5")
        .then(function (r) { return r.json() })
        .then(function(data) {
            if (!data.length) return
            locationsList.innerHTML = data.map(l => {
                return "<option value='" + l.nom + "'></option>";
            })
        });
    }
});
