// Requires JSCookie

// Set up jQuery AJAX to include CSRF tokens
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

function quickAjax(obj) {
    if (obj.url === undefined) {
        obj.url = $(location).attr('href');
    }
    $.ajax({
        beforeSend: setToken,
        type: 'POST',
        url: obj.url,
        data: obj.data,
        dataType: 'json',
        success: obj.success
    });
}