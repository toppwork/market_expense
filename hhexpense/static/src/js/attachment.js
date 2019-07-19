function _onAttachmentViewPdf(self){
    console.log('you are in attachment pdf part');
    var path = self.nextElementSibling.href;
    path = path.replace('?download=1','');
    console.log(path);
    window.open(path);
}

function _onAttachmentViewImg(self){
    console.log('you are in attachment view part');
    var path = self.src;
    console.log(path);
    window.open(path);
}

function _onAttachmentDownloadImg(self){
    //console.log(self.getAttribute('data-id'))
    var name = self.getAttribute('data-name').split(',')[1]
    console.log(name);
    console.log(self);
    var link = document.createElement("a");
    link.download = name;
    link.href = self.getAttribute('data-id');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    delete link;
}




