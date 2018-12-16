// Change which tab of content is currently being displayed
function changeTab(ev, tabName) {
	// Hide all the tab contents
	var contents = document.getElementsByClassName('tabContent');
	for (var i = 0; i < contents.length; i++) {
		contents[i].className = contents[i].className.replace(' active', '');
	}
	// Deactivate all the buttons
	var buttons = document.querySelectorAll('div.tab button');
	for (var i = 0; i < buttons.length; i++) {
		buttons[i].className = '';
	}
	// Activate the button clicked
	ev.currentTarget.className = 'active';
	// Show the selected tab contents
	document.getElementById(tabName).className += ' active';
}