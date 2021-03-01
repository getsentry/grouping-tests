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

    var eventCompareLeft = null;

    document.querySelectorAll('.compare-events').forEach(a => {
        a.addEventListener('click', (event) => {
            event.preventDefault();

            if(eventCompareLeft){
                if(eventCompareLeft != a) {
                    compareEvents(eventCompareLeft.href, a.href);
                }
                a.className = "";
                    a.querySelector('i').className = "bi-file-diff";
                    eventCompareLeft = null;
            } else {
                eventCompareLeft = a;
                a.className = "selected";
                a.querySelector('i').className = "bi-file-diff-fill";
            }
        });
    });
});

function compareEvents(leftURL, rightURL) {
    load(leftURL, function(left) {
        load(rightURL, function(right) {
            const diff = difflib.unifiedDiff(left.split(' '), right.split(' '));
            console.log(diff);
        });
    });
}

function load(url, callback) {
    const httpRequest = new XMLHttpRequest();

    httpRequest.onreadystatechange = function() {
        if (httpRequest.readyState === XMLHttpRequest.DONE) {
            if (httpRequest.status === 200) {
                callback(httpRequest.responseText);
            }
        }
    };
    httpRequest.open('GET', url);
    httpRequest.send();
}

