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
