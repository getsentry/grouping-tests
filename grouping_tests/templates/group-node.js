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

    document.querySelector('#collapse-all').addEventListener('click', () => {
        document.querySelectorAll('.collapser').forEach(item => {
            item.click();
        });
    });

    document.querySelectorAll('.open-sibling-diff').forEach(button => {
        button.addEventListener('click', (event) => {
            const button = event.target;

            const modal_selector = button.dataset.bsTarget;

            const modal = document.querySelector(modal_selector);
            const source_container = modal.querySelector("pre");
            const source = source_container.innerHTML;
            source_container.className += " d-none"

            const target = modal.querySelector(modal_selector+"-dynamic-content");

            var diffHtml = Diff2Html.html(source, {
                drawFileList: false,
                matching: 'lines',
                outputFormat: 'side-by-side',
            });
            target.innerHTML = diffHtml;
        });
    });

    {% include 'tree-chart.js' %}{# Abusing template include for js #}
});