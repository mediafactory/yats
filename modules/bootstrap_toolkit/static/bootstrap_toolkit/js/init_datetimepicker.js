(function($){
    $(function() {
         $('.form_datetime').datetimepicker(
           {
                   format: "dd.mm.yyyy HH:ii",
                   autoclose: true,
                   todayBtn: true
            }
         );
    })
})(jQuery);
