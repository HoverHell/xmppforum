function $(selector) {
  return bonzo(qwery(selector));
}

// AJAX-loaded forms
function t_e(id) { return load_form('action=geteditform&oid='+id); }
function t_r(id) { return load_form('action=getreplyform&oid='+id); }

function load_form(action) {
  var container = $('#replies');
  container.html("<p>" + "Processing..." + "</p>");
  var request = reqwest({
    url: SNAPBOARD_URLS.rpc_action, 
    type: 'json', 
    method: 'post', 
    data: action, 
    error: function (err) { container.html('<p><b>Error:</b>'+ err.responseText +'</p>') },
    success: function (resp) { container.html(resp.html) }
  }); 
  return false; 
}

// Thread level functions
function set_csticky(id) { return load_message('action=csticky&oclass=thread&oid='+id);}
function set_gsticky(id) { return load_message('action=gsticky&oclass=thread&oid='+id);}
function set_close(id) { return load_message('action=close&oclass=thread&oid='+id);}

// Post level function
function s_w(id) { return load_message('action=watch&oclass=post&oid='+id); }
function s_c(id) { return load_message('action=censor&oclass=post&oid='+id); }
function s_a(id) { return load_message('action=abuse&oclass=post&oid='+id); }

function load_message(action) {
  var container = $('#replies');
  container.html("<p>" + "Processing..." + "</p>");
  
  var request = reqwest({
    url: SNAPBOARD_URLS.rpc_action, 
    type: 'json', 
    method: 'post', 
    data: action, 
    error: function (err) { container.html('<p><b>Error:</b>'+ err.responseText +'</p>') },
    success: function (resp) { container.html('<p><b>Success:</b>' + resp.msg + ' <a href="">' +resp.link + '</a>?</p>') }
  });
  return false; 
}

function preview(form_id, parent) {
  var text = $('#'+form_id).val();
  var parentpost = $('.nf[id='+parent+']');
  var request = reqwest({
    url: SNAPBOARD_URLS.rpc_preview, 
    type: 'json', 
    method: 'post', 
    data: text, 
    error: function (err) { parentpost.append(err.responseText) },
    success: function (resp) { parentpost.append(
	'<div class="fp l"><div class="h"><div><div><div class="hm"> <b>Username</b>: post preview </div></div></div></div><div><div class="v" style="margin-left:6px"><div id="preview" class="t"><div>' + resp.preview + '</div></div></div></div></div>'
	) }
  });
return false; 
}


/*Hide|unhide thread | written in pure JS */
function xpath(path, root, type) {
  if(type)
    return document.evaluate(path, root || document, null, 8, null).singleNodeValue;
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
  each(xp, function(e){
    e.addEventListener('click', function(){
      switchid(this.id.split('_')[0]);
    }, false);
  })
}
window.onload = function() {
  build();
}

// Rudimentary and partially nonfunctional code. ToDo: Upgrade to new or delete.
function rev(orig_id, show_id) {
 urlq = SNAPBOARD_URLS.rpc_postrev + '?orig=' + orig_id + '&show=' + show_id;
 div_text = document.getElementById('pt' + orig_id);
 div_links = document.getElementById('prl' + orig_id);
 var handleSuccess = function(o) {
  if(o.responseText !== undefined) {
   res = eval('(' + o.responseText + ')');
   div_text.innerHTML = res['text'];
   // create links content
   links_html = '';
   if(res['prev_id'] !== '') {
    links_html += '<a href="#post' + orig_id + '" onClick="rev(\'';
    links_html += orig_id + '\',\'' + res['prev_id'];
    links_html += '\');">&#171; ' + 'previous' + '</a>';}
   links_html += gettext('This message has been revised')
   if(res['rev_id'] !== '') {
    links_html += '<a href="#post' + orig_id + '" onClick="rev(\'';
    links_html += orig_id + '\',\'' + res['rev_id'];
    links_html += '\');">' + 'next' + ' &#187;</a>';}
   div_links.innerHTML = links_html;}};
 var handleFailure = function(o) {
  var errordiv = document.getElementById("thread_rpc_feedback");
  if(o.responseText !== undefined) {
   for (var n in o) {
    if (o.hasOwnProperty(n)) {
     errordiv.innerHTML += o[n];}}}};
 var callback = {
  success:handleSuccess,
  failure:handleFailure,
  argument: []};
 var request = YAHOO.util.Connect.asyncRequest('GET', urlq, callback, null);}


function get_ta() { return document.getElementById('add_post_div').elements['post'];}

function surround(tag, ctag) {
 var ta = get_ta();
 if (!ctag) {
  ctag = tag;}
 if (document.selection) {
  ta.focus();
  var selection = document.selection.createRange();
  selection.text = tag + selection.text + ctag;} 
 else if (ta.selectionStart >= 0) {
  var val = ta.value;
  ta.value = val.substring(0, ta.selectionStart) + tag + val.substring(ta.selectionStart, ta.selectionEnd) + ctag + val.substring(ta.selectionEnd, val.length);} 
 else {
  ta.value += tag + ctag}
 return false;}

function do_prefix(tag) {
 var ta = get_ta();
 if (document.selection) {
  ta.focus();
  var selection = document.selection.createRange();
  text = selection.text;
  selection.text = '\n' + tag + text.replace(/\n/g,'\n' + tag) + '\n';} 
 else if (ta.selectionStart >= 0) {
  var val = ta.value;
  pref = ta.selectionStart && val.substring(ta.selectionStart - 1, ta.selectionStart) != '\n' ? '\n' : '';
  ta.value = val.substring(0, ta.selectionStart) + pref + tag + val.substring(ta.selectionStart, ta.selectionEnd).replace(/\n/g, '\n' + tag) + '\n' + val.substring(ta.selectionEnd, val.length);} 
 else {
  ta.value += '\n' + tag;}
 return false;}

function do_insert(tag) {
 var ta = get_ta();
 if (document.selection) {
  ta.focus();
  var selection = document.selection.createRange();
  text = selection.text;
  selection.text = tag;} 
 else if (ta.selectionStart >= 0) {
  var val = ta.value;
  ta.value = val.substring(0, ta.selectionStart) + tag + val.substring(ta.selectionEnd, val.length);} 
 else {
  ta.value += '\n' + tag;}
 return false;}

function insert_img(url, name, title) {
 if (!url) {
  url = prompt('What is the URL of the image?', '');
  if (!url) {
   return false;}}
 if (!name) {
  name = prompt('What is the title of the image?');
  if (!name) {
   name = '';}}
 if (!title) {
  title = name;}
 return do_insert('[img' + (name ? '=' + name : '') + ']' + url + '[/img]')}

function insert_link(url, name) {
 if (!url) {
  url = prompt('What is the URL of the link?', '');
  if (!url) {
   return false;}}
 if (!name) {
  name = prompt('What is the title of the link?');
  if (!name) {
   name = url;}}
 return do_insert('[url=' + url + ']' + name + '[/url]')}

function find_textarea (el) { return true; }// el.tagName.toLowerCase() == 'textarea'; }
