
document.addEventListener('DOMContentLoaded', () => {

    document.querySelectorAll('.compare-events').forEach(a => {
        a.addEventListener('click', (event) => {
            event.preventDefault();
            setCompareState(() => {
                const leftURL = localStorage.getItem("compare-left-url");
                if(leftURL === null) {
                    localStorage.setItem("compare-left-url", a.href);
                } else {
                    if(leftURL == a.href) {
                        // Clicked again, remove
                        localStorage.removeItem("compare-left-url");
                    } else {
                        // Clicked a 2nd event, set as right url
                        localStorage.setItem("compare-right-url", a.href);
                    }
                }
            });
        });
    });

    document.getElementById("clear-comparison").addEventListener('click', (event) => {
        event.preventDefault();
        setCompareState(() => {
            localStorage.removeItem("compare-left-url");
            localStorage.removeItem("compare-right-url");
        });
    });

    document.getElementById("compare-modal").addEventListener('hidden.bs.modal', function () {
        setCompareState(() => {
            localStorage.removeItem("compare-left-url");
            localStorage.removeItem("compare-right-url");
        });
    })

    setCompareState();
});


/// Execute given function and refresh compare elements
function setCompareState(fn) {

    if(fn) fn();

    renderCompareButtons();
    renderCompareFooter();
    renderCompareModal();
}

function renderCompareButtons() {
    const leftURL = localStorage.getItem("compare-left-url");
    document.querySelectorAll('.compare-events').forEach(a => {
        if(leftURL == a.href) {
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
    if(localStorage.getItem("compare-left-url")) {
        footer.classList.add("show");
    } else {
        footer.classList.remove("show");
    }
}

function renderCompareModal() {
    const modal = new bootstrap.Modal(document.getElementById("compare-modal"));
    if(localStorage.getItem("compare-left-url") && localStorage.getItem("compare-right-url")) {
        modal.show();
    } else {
        modal.hide();
    }
}



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