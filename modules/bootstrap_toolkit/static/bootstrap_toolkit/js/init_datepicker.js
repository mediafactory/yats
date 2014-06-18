(function($){
    $(document).on('focus.django-bootstrap-toolkit.data-api click.django-bootstrap-toolkit.data-api', 'div.controls .input-append.date', function (e) {
    	if (e.target.nodeName == 'INPUT')
			$(e.target).datepicker("show");
		else {
			$(e.target.parentElement.parentElement.children[0]).datepicker("show");
		}
    });
    
})(jQuery);
