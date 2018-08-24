(function($){
    $(function() {
         $('.form_datetime').datetimepicker(
           {
                   format: "dd.mm.yyyy hh:ii",
                   autoclose: true,
                   todayBtn: true
            }
         );
    })
})(jQuery);
