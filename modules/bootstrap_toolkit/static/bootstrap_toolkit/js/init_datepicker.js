(function($){
    $(document).on('focus.django-bootstrap-toolkit.data-api click.django-bootstrap-toolkit.data-api', 'input[data-bootstrap-widget=datepicker][data-provide!="datepicker"]', function (e) {
        $(e.target).datepicker("show");
    });
    
    $(function() {
        $('input[data-bootstrap-widget=datepicker][data-provide!="datepicker"]').datepicker({
            todayBtn: 'linked',
            todayHighlight: true
        });
    })
})(jQuery);
