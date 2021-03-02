document.addEventListener('DOMContentLoaded', () => {

    document.querySelectorAll('.collapser').forEach(button => {
        button.addEventListener('click', (event) => {
            event.preventDefault();
            const icon = button.querySelector("i");
            if(button.classList.contains("collapsed")) {
                icon.className = "bi-chevron-right";
            } else {
                icon.className = "bi-chevron-down";
            }
        });
    });

    const collapseAll = document.querySelector('#collapse-all');
    if(collapseAll) collapseAll.addEventListener('click', () => {
        document.querySelectorAll('.collapser').forEach(item => {
            item.click();
        });
    });
});



