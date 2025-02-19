// Scroll today's table to current time column

var scrollEl = document.querySelector("th.cell_past ~ th:not(.cell_past)");

var scrollElWrapper = scrollEl?.closest(".table-container");
scrollElWrapper && scrollElWrapper.scroll({
    left: scrollEl.offsetLeft - scrollElWrapper.offsetWidth / 2,
    behavior: 'smooth'
});
