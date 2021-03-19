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
    if(issueFilter) {

        // Populate searchables:
        document.querySelectorAll('.group-box').forEach(el => {
            const content = el.querySelector(':scope > .parent').textContent;
            el.dataset.searchableContent = content.toLowerCase();
        });

        var updateFilter;
        issueFilter.addEventListener('input', event => {
            if(updateFilter) clearTimeout(updateFilter);
            updateFilter = setTimeout(() => {
                const searchString = event.target.value.toLowerCase();
                document.querySelectorAll('#issues>.group-box').forEach(el => {
                    showIfContains(el, searchString);
                });
            }, 200);
        });
    }

    document.querySelectorAll('.favorite').forEach(el => {
        el.addEventListener('click', (event) => {
            event.preventDefault();
            if(el.classList.contains('bi-star-fill')) {
                el.classList.remove('bi-star-fill');
                el.classList.add('bi-star');
                removeFavorite(el.dataset.node);
            } else {
                el.classList.add('bi-star-fill');
                el.classList.remove('bi-star');
                addFavorite(el.dataset.node);
            }
        });
    });

    initFavorites();

});

function addFavorite(nodeName) {
    const favorites = localStorage.getItem("favorites");
    localStorage.setItem("favorites",
        favorites ? (favorites + "," + nodeName) : nodeName
    );
}

function removeFavorite(nodeName) {
    const favoritesStr = localStorage.getItem("favorites");
    if(favoritesStr) {
        var favorites = new Set(favoritesStr.split(","));
        favorites.delete(nodeName);
        localStorage.setItem("favorites", Array.from(favorites).join(","));
    }
}

function initFavorites() {
    const favoritesStr = localStorage.getItem("favorites");
    if(favoritesStr) {
        var favorites = new Set(favoritesStr.split(","));
        favorites.forEach(nodeName => {
            const el = document.getElementById("favorite-" + nodeName);
            if(el) {
                el.classList.add('bi-star-fill');
                el.classList.remove('bi-star');
            }
        })
    }
}

function showIfContains(el, searchString) {

    var show = false;
    el.querySelectorAll('.children > .group-box').forEach(child => {
        // If any child contains the text, we can show the parent
        show |= showIfContains(child);
    });

    // If necessary, really search
    show = show || el.dataset.searchableContent.search(searchString) >= 0;
    if( show ) {
        el.classList.remove('d-none');
    } else {
        el.classList.add('d-none');
    }
}
