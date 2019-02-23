// Requires jQuery, JSCookie

var TAB_COOKIE = true;

// Change which tab of content is currently being displayed
function changeTab(ev, tabName) {
    var button = $(ev.target);
    
    if (TAB_COOKIE) {
        Cookies.set('tab', tabName, {path: location.pathname});
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