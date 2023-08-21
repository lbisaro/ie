/**
 * 
 * @param {*} url '{% url "url_name" %}'
 * @param {*} data {
                    data_a: $('#data_a').val(),
                    data_b: $('#data_b').val(),
                }
 */
var ajxRsp;
function get_ajax(url,data) {
    spinner_show();
    if (data)
    {
        data.csrfmiddlewaretoken = $('input[name=csrfmiddlewaretoken]').val();
        data.action =  'post';
    }
    else
    {
        data = {
            csrfmiddlewaretoken: $('input[name=csrfmiddlewaretoken]').val(),
            action: 'post',
        }        
    }
    return $.ajax({
        type: 'POST',
        url: url,
        data: data,
        error: function (xhr, errmsg, err) {
            console.log(xhr.status + ": " + xhr.responseText); 
        }
    }).done(function () {
        spinner_hide();
    });
}

function spinner_show()
{
    $('#ajax_spinner').show();
}

function spinner_hide()
{
    $('#ajax_spinner').hide();
}

function html_alert(title, text, cls) {
    var html = '<span class="' + cls + '">' + text + '</span>';
    $('#html_alert_title').html(title)
    $("#html_alert_body").html(html);
    $('#html_alert').show();
}

window.alert = function(msg,el,isError) {
    var cls = 'text-primary';
    if (isError)
        var cls = 'text-danger';
    html_alert('Alerta!',msg,cls);
    console.log(msg);
    return;
}

