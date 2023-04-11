function getPasteValue(evt, elem, callback) {
    setTimeout(function () {
        callback(elem, elem.val())
    }, 100);
    // if (navigator.clipboard && navigator.clipboard.readText) {
    //     // modern approach with Clipboard API
    //     //navigator.clipboard.readText().then(callback);
    // } else if (evt.originalEvent && evt.originalEvent.clipboardData) {
    //     // OriginalEvent is a property from jQuery, normalizing the event object
    //     callback(elem, evt.originalEvent.clipboardData.getData('text'));
    // } else if (evt.clipboardData) {
    //     // used in some browsers for clipboardData
    //     callback(elem, evt.clipboardData.getData('text/plain'));
    // } else if (window.clipboardData) {
    //     // Older clipboardData version for Internet Explorer only
    //     callback(elem, window.clipboardData.getData('Text'));
    // } else {
    //     // Last resort fallback, using a timer
    //     setTimeout(function () {
    //         callback(elem.val())
    //     }, 100);
    // }
}

function setPasteInputValue(input, value) {
    if (value) {
        input.val(value.trim());
    }
}