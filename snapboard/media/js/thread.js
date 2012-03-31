//function $(selector) {
//  return bonzo(qwery(selector));
//}

// AJAX-loaded forms
function t_e(id) { return load_form('action=geteditform&oid='+id); }
function t_r(id) { return load_form('action=getreplyform&oid='+id); }

function load_form(action) {
  var container = $('#forms');
  var w_container = $('#warnings');
  container.html("<p>" + "Processing..." + "</p>");
  var errorProcess = function (err) { err.w_container.html('<p><a onclick="cleardiv(\'warnings\')" class="cl">close</a> <b>Error:</b> '+ err.responseText +'</p>') };
  var successProcess = function (resp) { container.html(resp.html) };
  rpc_request(action, errorProcess, successProcess);
  return false; 
}

// Thread level functions
function set_csticky(id) { return load_message('action=csticky&oclass=thread&oid='+id);}
function set_gsticky(id) { return load_message('action=gsticky&oclass=thread&oid='+id);}
function set_close(id) { return load_message('action=close&oclass=thread&oid='+id);}

// Post level function
function s_w(id) { 
return load_message('action=watch&oclass=post&oid='+id); 
$('.l[id=snap_post'+id+']').hide();  //supposed to work on watchlist.html page, but doesn't
}
function s_c(id) { return load_message('action=censor&oclass=post&oid='+id); }
function s_a(id) { return load_message('action=abuse&oclass=post&oid='+id); }

function load_message(action) {
  var w_container = $('#warnings');
  w_container.html("<p>" + "Processing..." + "</p>");
  var errorProcess = function (err) { w_container.html('<p><a onclick="cleardiv(\'warnings\')" class="cl">close</a> <b>Error:</b> '+ err.responseText +'</p>') };
  var successProcess = function (resp) { w_container.html('<p><a onclick="cleardiv(\'warnings\')" class="cl">close</a> <b>Success:</b> ' + resp.msg + ' <a href="">' +resp.link + '</a></p>')};
  rpc_request(action, errorProcess, successProcess);
  return false;
}

function preview(form_id, parent) {
  var text = $('#'+form_id).val();
  var parentpost = $('.post[id='+parent+']');
  var w_container = $('#warnings');
  var url = SNAPBOARD_URLS.rpc_preview;

  var errorProcess = function (err) { w_container.html('<p><a onclick="cleardiv(\'warnings\')" class="cl">close</a> <b>Error:</b> '+err.responseText+'</p>') };
  var successProcess = function (resp) { parentpost.append(	'<div class="fp l"><div class="h"><div><div><div class="hm"> <b>Username</b>: post preview </div></div></div></div><div><div class="v" style="margin-left:6px"><div id="preview" class="t"><div>' + resp.preview + '</div></div></div></div></div>' )};
  rpc_request(text, errorProcess, successProcess, url);
  return false; 
}

function rpc_request(action, errorProcess, successProcess, url) {
    var request = $.post(
        url || SNAPBOARD_URLS.rpc_action,
        action,
        function(data, textStatus, jqXHR){ successProcess(data) },
        'json'
     ).fail(
         function(jqXHR, textStatus){ errorProcess(textStatus) }); 
    return false;
  var request = $.post(url || SNAPBOARD_URLS.rpc_action, {
    dataType: 'json', 
    data: action, 
  }).done(successProcess).fail(errorProcess); 
  return false; 
}

function cleardiv(what) { // Universal html wipe 
  $('div[id='+what+']').html('');
  return false; 
}
function masscollapse() {
  $('.fold').toggleClass('hidden');
  // 
  // Для каждого поста .post(id) (как это сделать?)
  // Взять 10 первых слов из .fold
  // Append их в конец .hm в спецблоке (обертка <div class="quotewrap">) этого .post
  // Скрыть в .ht лишние ссылки и дату (.time .un )
  //
  // Наоборот: показать ссылки и дату, удалить спецблок, показать .fold
  //
  return false; 
}
function toggle(element) { // Universal toggle visibility (not tested yet)
  $('*[id='+element+']').toggleClass('hidden');
  return false;
}


/*Hide|unhide thread | written in pure JS */
function xpath(path, root, type) {
  if(type) return document.evaluate(path, root || document, null, 8, null).singleNodeValue;
  else {
    var r = document.evaluate(path, root || document, null, 6, null), a = [];
    for(var i=0;i<r.snapshotLength;i++) 
      a.push(r.snapshotItem(i));
    return a;
  }
}
function each(list, func) { 
  for(var i=0;i<list.length;i++)
    func(list[i],i);
}
function switchid(id) {
  var elink = document.getElementById(id+'_a');
  var ediv = document.getElementById(id+'_d');
  var ehead = document.getElementById('inh'+id);
	
  if(ediv.style.display == 'none') {
    ediv.style.display = 'block';
    elink.innerHTML = '-';  
    ehead.style.borderBottomWidth = '0px';
  } else {
    ediv.style.display = 'none';
    elink.innerHTML = '+';
    ehead.style.borderBottomWidth = '1px';
  }
}
function build() {
  var xp = xpath('.//a[contains(@class,"hide")]');
  each(xp, function(e) {
    /*
    e.addEventListener('click', function(){
      switchid(this.id.split('_')[0]);
    }, false);
    */
    e.onclick = function(){
      switchid(this.id.split('_')[0]);
      return false;
    };
  });
  // TODO: test it.
    $(".reply").each(function(i, e) {
        p_id = $(e).parents(".h")[0].id;
        e.onclick = function(){
            t_r(p_id);
            return false;
        };
    });
}
window.onload = function() {
  build();
}
