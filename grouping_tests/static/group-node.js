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

    document.querySelectorAll('.copy-to-clipboard').forEach(button => {
        button.addEventListener('click', (event) => {
            const sourceEl = document.getElementById(button.dataset.source);
            const source = sourceEl.innerText;
            navigator.clipboard.writeText(sourceEl.innerText).then(value => {
                button.innerText = "Copied.";
                button.disabled = "disabled";
            })
        });
    });
});



