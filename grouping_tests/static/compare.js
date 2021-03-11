
document.addEventListener('DOMContentLoaded', () => {

    document.querySelectorAll('.compare-events').forEach(a => {
        a.addEventListener('click', (event) => {
            event.preventDefault();
            setCompareState(() => {
                const leftURL = localStorage.getItem("compare-left-url");
                if (leftURL === null) {
                    localStorage.setItem("compare-left-url", normalizeURL(a.href));
                } else {
                    if (leftURL == a.href) {
                        // Clicked again, remove
                        localStorage.removeItem("compare-left-url");
                    } else {
                        // Clicked a 2nd event, set as right url
                        localStorage.setItem("compare-right-url", normalizeURL(a.href));
                    }
                }
            });
        });
    });

    // Clear all compare state when user clicks on "Clear"
    document.getElementById("clear-comparison").addEventListener('click', (event) => {
        event.preventDefault();
        setCompareState(() => {
            localStorage.removeItem("compare-left-url");
            localStorage.removeItem("compare-right-url");
        });
    });

    // Compare events when modal is shown
    document.getElementById("compare-modal").addEventListener('show.bs.modal', compareEvents);

    // Clear all compare state when modal is closed
    document.getElementById("compare-modal").addEventListener('hidden.bs.modal', function () {
        document.getElementById("compare-modal-body").innerHTML = '';
        setCompareState(() => {
            localStorage.removeItem("compare-left-url");
            localStorage.removeItem("compare-right-url");
        });
    });

    // Render compare elements on page load
    setCompareState();
});


/// Execute given function and refresh compare elements
function setCompareState(fn) {

    if (fn) fn();

    renderCompareButtons();
    renderCompareFooter();
    renderCompareModal();
}

function renderCompareButtons() {
    const leftURL = localStorage.getItem("compare-left-url");
    document.querySelectorAll('.compare-events').forEach(a => {
        if (leftURL == a.href) {
            a.classList.add("selected");
            a.querySelector('i').className = "bi-file-diff-fill";
        } else {
            a.classList.remove("selected");
            a.querySelector('i').className = "bi-file-diff";
        }
    });
}

function renderCompareFooter() {
    const footer = document.getElementById("compare-footer");
    if (localStorage.getItem("compare-left-url") && !localStorage.getItem("compare-right-url")) {
        footer.classList.add("show");
    } else {
        footer.classList.remove("show");
    }
}

function renderCompareModal() {
    const modal = new bootstrap.Modal(document.getElementById("compare-modal"));
    if (localStorage.getItem("compare-left-url") && localStorage.getItem("compare-right-url")) {
        modal.show();
    } else {
        modal.hide();
    }
}

function compareEvents() {
    const leftURL = localStorage.getItem("compare-left-url");
    const rightURL = localStorage.getItem("compare-right-url");

    document.getElementById("compare-modal-body").innerHTML = "Loading...";

    var left = null;
    var right = null;

    function onSuccess() {

        if( !(left && right) ) {
            return;
        }

        const diff = difflib.unifiedDiff(
            left.split('\n'),
            right.split('\n'),
            {n: 1000}, // Make sure the whole file is visible
        );

        const fullDiff = "diff --git a/foo b/foo\n" + diff.join("\n");

        var diffHtml = Diff2Html.html(fullDiff, {
            drawFileList: false,
            matching: 'lines',
            outputFormat: 'side-by-side'
        });

        document.getElementById("compare-modal-body").innerHTML = diffHtml;
    }

    load(leftURL, data => { left = data; onSuccess(); });
    load(rightURL, data => { right = data; onSuccess(); });
}

function load(url, callback) {
    const httpRequest = new XMLHttpRequest();

    httpRequest.onreadystatechange = function () {
        if (httpRequest.readyState === XMLHttpRequest.DONE) {
            if (httpRequest.status === 200) {
                callback(httpRequest.responseText);
            }
        }
    };
    httpRequest.open('GET', url);
    httpRequest.send();
}

function normalizeURL(href) {
    return new URL(href, window.location.href).href
}
