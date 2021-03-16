document.addEventListener('DOMContentLoaded', () => {

    const collapseAll = document.querySelector('#collapse-all');
    if(collapseAll) collapseAll.addEventListener('click', (event) => {
        event.preventDefault();
        document.querySelectorAll('.collapse').forEach(el => {
            const collapse = bootstrap.Collapse.getInstance(el) || new bootstrap.Collapse(el);
            collapse.hide();
        });
    });

    const expandAll = document.querySelector('#expand-all');
    if(expandAll) expandAll.addEventListener('click', (event) => {
        event.preventDefault();
        document.querySelectorAll('.collapse').forEach(el => {
            const collapse = bootstrap.Collapse.getInstance(el) || new bootstrap.Collapse(el);
            collapse.show();
        });
    });

    document.querySelectorAll('.collapse').forEach(el => {
        el.addEventListener('show.bs.collapse', () => {
            const handle = document.getElementById(el.dataset.handle);
            handle.querySelector('i').className = 'bi-chevron-down';
        });
        el.addEventListener('hide.bs.collapse', () => {
            const handle = document.getElementById(el.dataset.handle);
            handle.querySelector('i').className = 'bi-chevron-right';
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

    const toggleCardinality = document.getElementById('toggle-cardinality');
    if(toggleCardinality) toggleCardinality.addEventListener('change', event => {
        if(event.target.checked) {
            renderTreeChart(treeChartData, true);
        } else {
            renderTreeChart(treeChartData, false);
        }
    });

    const issueFilter = document.getElementById('issue-filter');
    if(issueFilter) issueFilter.addEventListener('input', event => {
        const searchString = event.target.value.toLowerCase();
        document.querySelectorAll('.group-box').forEach(el => {
            if(el.textContent.toLowerCase().search(searchString) >= 0) {
                el.classList.remove('d-none');
            } else {
                el.classList.add('d-none');
            }
        });
    })

});
