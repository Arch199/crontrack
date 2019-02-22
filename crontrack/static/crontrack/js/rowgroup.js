// Requires jQuery

// Toggle opening or closing a rowGroup
function toggleRowGroup(ev) {
    // Ignore clicks on input elements
    if ($(ev.target).is('input')) return;
    
    // Toggle the next content object and this one
    var content = $(ev.target).closest('tbody').next('.rowGroupContent').toggleClass('open');
    $(ev.target).toggleClass('open');
}

// Toggle opening or closing a rowGroupItem
function toggleRowGroupItem(ev) {
    // Ignore clicks on input elements
    if ($(ev.target).is('input')) return;
    
    // Toggle the item and item info objects
    var info = $(ev.target).next('.rowGroupItemInfo').toggleClass('open');
    $(ev.target).closest('.rowGroupItem').toggleClass('open');
}

// Ask for confirmation for deleting a row group
function deleteRowGroup(ev, groupName) {
    response = confirm('Are you sure you want to delete the group "' + groupName + '"?\nThis cannot be undone.');
    if (response) {
        $('#deleteRowGroupForm').submit();
    }
}

// Ask for confirmation for deleting a row item
function deleteRowGroupItem(ev, itemName) {
    response = confirm('Are you sure you want to delete the item "' + itemName + '"?\nThis cannot be undone.');
    if (response) {
        //document.getElementById('deleteRowGroupItemInput').value = itemID;
        //document.getElementById('deleteRowGroupItemForm').submit();
        var itemID = $(ev.target).closest('tr').attr('id');
        quickAjax({
            data: {
                itemID: itemID
            },
            success: data => {
                $('#' + data.itemID).remove();
            },
            url: $(ev.target).attr('my-url')
        });
    }
}