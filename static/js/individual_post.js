const container = document.querySelector('.similar-posts');

if (container) {
    container.addEventListener('wheel', function (e) {
        if (e.deltaY === 0) return;

        const maxScrollLeft = container.scrollWidth - container.clientWidth;
        const atStart = container.scrollLeft === 0;
        const atEnd = container.scrollLeft === maxScrollLeft;

        if ((e.deltaY < 0 && !atStart) || (e.deltaY > 0 && !atEnd)) {
            e.preventDefault();
            container.scrollLeft += e.deltaY * 2;
        }
    }, { passive: false })
}
