// Toggle opening or closing a rowGroup
function toggleRowGroup(ev) {
	// Ignore clicks on input elements
	if (ev.target.tagName.toLowerCase() == 'input') return;
	
	// Find the next rowGroupContent object
	var content = ev.currentTarget.parentNode.parentNode.nextElementSibling;
	// ^ current node is <td>, parent 1 is <tr>, parent 2 is <tbody> 
	while (!content.className.includes('rowGroupContent')) {
		console.log('Got className = ' + content.className);
		console.log(content);
		content = content.nextElementSibling;
	}
	
	// Toggle being open or closed
	toggleOpen(ev.currentTarget, [content]);
}

// Toggle opening or closing a rowGroupItem
function toggleRowGroupItem(ev) {
	// Ignore clicks on input elements
	if (ev.target.tagName.toLowerCase() == 'input') return;
	
	// Find the next rowGroupItemInfo object
	var info = ev.currentTarget.nextElementSibling;
	if (!info.className.includes('rowGroupItemInfo')) return;
	
	// Toggle being open or closed
	toggleOpen(ev.currentTarget, [info]);
}

// Generic helper function for toggling open/closed
function toggleOpen(leader, others=[]) {	
	if (leader.className.includes(' open')) {
		leader.className = leader.className.replace(' open', '');
		others.forEach(function(item) {
			item.className = item.className.replace(' open', '')
		});
	} else {
		leader.className += ' open';
		others.forEach(function(item) {
			item.className += ' open';
		});
	}
}

// Ask for confirmation for deleting a row group
function deleteRowGroup(ev, groupName) {
	response = confirm('Are you sure you want to delete the group "' + groupName + '"?\nThis cannot be undone.');
	if (response) {
		document.getElementById('deleteForm').submit();
	}
}