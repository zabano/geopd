/***********************************************************************************************************************
 * GEoPD JavaScript Library
 **********************************************************************************************************************/

geopd = {}

geopd.dom = {}


/***********************************************************************************************************************
 * Document Initialization
 **********************************************************************************************************************/

$(document).ready(function () {

    $.extend(true, $.fn.dataTable.defaults, {
        drawCallback: function () {
            $('[data-toggle="tooltip"]').addClass('tip-auto').tooltip();
        },
        columnDefs: [{
            targets: '_all',
            defaultContent: can.dom.label('NA', 'Not Available', 'warning'),
        }],
        processing: true,
    });

    $.extend(true, $.fn.editable.defaults, {
        name: 'value',
        id: 'name',
        cancel: '<button class="btn btn-sm btn-default" type="cancel" >' +
        '<span class="glyphicon glyphicon-remove"></span></button>',
        submit: '<button class="btn btn-sm btn-primary" type="submit" >' +
        '<span class="glyphicon glyphicon-ok"></span></button>',
        indicator: 'Saving ...',
    });

    var csrftoken = $('meta[name=csrf-token]').attr('content');

    $.ajaxSetup({
        headers: { 'X-CSRFToken': csrftoken }
    });

    $('[data-toggle="tooltip"]').addClass('tip-auto').tooltip();

    $('time[data-moment]').each(function (i, time) {
        var data = moment($(time).attr('data-moment'));
        $(time).html(data.fromNow()).attr('title', data.format('MMMM D YYYY h:mm A')).addClass('tip-auto').tooltip();
    });

    $('.collapse')
        .on('shown.bs.collapse', function () {
            $(this)
                .parent()
                .find(".glyphicon-chevron-down")
                .removeClass("glyphicon-chevron-down")
                .addClass("glyphicon-chevron-up");
        })
        .on('hidden.bs.collapse', function () {
            $(this)
                .parent()
                .find(".glyphicon-chevron-up")
                .removeClass("glyphicon-chevron-up")
                .addClass("glyphicon-chevron-down");
        });
});
