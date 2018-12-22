// Toggle opening or closing a rowGroup
function toggleRowGroup(ev) {
	// Find the next rowGroupContent object
	var content = ev.currentTarget.parentNode.parentNode.nextElementSibling;
	// ^ current node is <td>, parent 1 is <tr>, parent 2 is <tbody> 
	while (!content.className.includes('rowGroupContent')) {
		console.log('Got className = ' + content.className);
		console.log(content);
		content = content.nextElementSibling;
	}
	
	// Toggle being open or closed
	if (ev.currentTarget.className.includes(' open')) {
		ev.currentTarget.className = ev.currentTarget.className.replace(' open', '');
		content.className = content.className.replace(' open', '');
	} else {
		ev.currentTarget.className += ' open';
		content.className += ' open';
	}
}