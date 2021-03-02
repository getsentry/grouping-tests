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

    document.querySelectorAll('.open-sibling-diff').forEach(button => {
        button.addEventListener('click', (event) => {
            const button = event.target;

            const modalSelector = button.dataset.bsTarget;

            const modal = document.querySelector(modalSelector);
            const sourceContainer = modal.querySelector("pre");
            const source = sourceContainer.innerHTML;
            sourceContainer.className += " d-none"

            const target = modal.querySelector(modalSelector+"-dynamic-content");

            var diffHtml = Diff2Html.html(source, {
                drawFileList: false,
                matching: 'lines',
                outputFormat: 'side-by-side',
            });
            target.innerHTML = diffHtml;
        });
    });
});



