geopd = {}

/***************
 * DOM Helpers *
 ***************/

geopd.dom = {}

geopd.dom.html = function (obj) {
    var tmp = $('<div/>').html(obj);
    return tmp.html();
}


geopd.dom.create_link = function(href, label, title) {

    var a = $('<a/>').attr('href', href).text(label);

    if (href.substr(0, 4) == 'http') {
        a.attr('target', '_blank')
    }

    if (title !== undefined) {
        a.attr('title', title).attr('data-toggle', 'tooltip')
    }

    return a;
}

geopd.dom.link = function(href, label, title) {
    return geopd.dom.html(geopd.dom.create_link(href, label, title));
}

geopd.dom.create_label = function(content, title, type, pad) {

    if (type === undefined) {
        type = 'default';
    }

    return $('<span/>').addClass('label label-' + type)
        .attr('title', title).text(content)
        .attr('data-toggle', 'tooltip');
}

geopd.dom.label = function(content, title, type) {
    return geopd.dom.html(geopd.dom.create_label(content, title, type));
}

geopd.dom.datetime = function(data) {
    if (data) {
        var date = moment(data);
        return geopd.dom.html($('<time/>').attr('title', date.format('MMMM D YYYY h:mm A')).text(date.fromNow()))
    }
}

/******************
 * Initialization *
 ******************/

$.extend(true, $.fn.dataTable.defaults, {
    drawCallback: function () {
        $('[data-toggle="tooltip"]').addClass('tip-auto').tooltip();
    },
    columnDefs: [{
        targets: '_all',
        defaultContent: geopd.dom.label('NA', 'Not Available', 'warning'),
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

var csrftoken = $('meta[name=csrf-token]').attr('content')

$.ajaxSetup({
    beforeSend: function(xhr, settings) {
        if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken)
        }
    }
})

$(document).ready(function () {

    $('[data-toggle="tooltip"]').addClass('tip-auto').tooltip();

    $('time.moment').each(function (i, time) {
        var data = moment($(time).html());
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