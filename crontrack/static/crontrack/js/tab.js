// Requires jQuery, JSCookie

var TAB_COOKIE = true;

// Change which tab of content is currently being displayed
function changeTab(ev, tabName) {
    // Check if this is on page load (needs to be faster and not set a cookie)
    if (event === undefined) {
        // An event hasn't been triggered; find the button before activating it
        var button = $('div.tab button[js-target="' + tabName + '"]');
    } else {
        var button = $(ev.target);
    }
    
    if (TAB_COOKIE) {
        Cookies.set('tab', tabName, {path: ''});
    }
    
    // Hide all tab content + deactivate all buttons
    $('.tabContent, div.tab button').each((i, el) => {
        $(el).removeClass('active');
    });
    
    // Activate the button clicked and show the tab content
    button.addClass('active');
    $('#' + button.attr('js-target')).addClass('active');
}

$(function() {    
    $('div.tab button').on('click', function(ev) {
        changeTab(ev, $(this).attr('js-target'));
    });
});