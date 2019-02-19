// Requires JSCookie

// Set up JQuery AJAX to include CSRF tokens
// more info here: https://docs.djangoproject.com/en/2.1/ref/csrf/#ajax

var csrfToken = Cookies.get('csrftoken');

function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}

function setToken(xhr, settings) {
    if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
        xhr.setRequestHeader("X-CSRFToken", csrfToken);
    }
}