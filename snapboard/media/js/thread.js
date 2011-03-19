function t_p(id) {
 toggle('ps'+id, 'inline');
 toggle('pv'+id, 'block');}

function t_e(id) {
 toggle('pt'+id, 'block');
 exttoggle('pe'+id, 
  'block',
  'action=geteditform&oid='+id);
 return false;}
 
function t_r(id) {
 exttoggle('pr'+id, 'block',
  'action=getreplyform&oid='+id);
 return false;}


function toggle(id, type) {
 var e = document.getElementById(id);
 if(e.style.display == 'none')
  e.style.display = type;
 else
  e.style.display = 'none';}

function exttoggle(id, type, action) {
 // on show retreives HTML code from RPC.
 var e = document.getElementById(id);
 if(e.style.display == 'none') {
  e.style.display = type;
  var handleSuccess = function(o) {
   if(o.responseText !== undefined) {
    res = JSON.parse(o.responseText);
    e.innerHTML = res.html;}};
  var handleFailure = function(o) {
   e.innerHTML = "<b>" + "ERROR." + "</b>";
   if(o.responseText !== undefined) {
    for (var n in o) {
     if (o.hasOwnProperty(n)) {
      e.innerHTML += o[n]+"<br/>";}}}};
  var callback = {
   success:handleSuccess,
   failure:handleFailure,
   argument:[]};
  e.innerHTML = "<b>" + "Processing..." + "</b>";
  var request = YAHOO.util.Connect.asyncRequest('POST', SNAPBOARD_URLS.rpc_action, callback, action);}
 else {
  e.style.display = 'none';}}

function preview(form_id) {
 urlq = SNAPBOARD_URLS.rpc_preview;
 form = document.getElementById(form_id);
 text = form.post.value;
 div_preview = document.getElementById('snap_preview_addpost');
 var handleSuccess = function(o) {
  if(o.responseText !== undefined) {
   res = eval('(' + o.responseText + ')');
   div_preview.innerHTML = res['preview'];
   div_preview.parentNode.style.display = 'block';}};
 var handleFailure = function(o) {
  var errordiv = document.getElementById("thread_rpc_feedback");
  if(o.responseText !== undefined) {
   div_preview.innerHTML = 'There was an error previewing your post.';
   div_preview.parentNode.style.display = 'block';}};
 var callback = {success:handleSuccess, failure:handleFailure, argument: []};
 YAHOO.util.Connect.setDefaultPostHeader(false);
 YAHOO.util.Connect.initHeader('Content-Type', 'text/plain', true);
 var request = YAHOO.util.Connect.asyncRequest('POST', urlq, callback, text);}

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


// --- yahoo connection stuff ---
function toggle_variable(action, oname, oclass, oid, msgdivid) {
 // This function sends an RPC request to the server to toggle a
 // variable (usually a boolean).  The server response with text
 // to replace the button clicked and a status message.
 // TODO: oid should be renamed as oid
 var postData = 'action=' + action + '&oclass=' + oclass + '&oid=' + oid;
 var div = document.getElementById(oname + oid);
 var msgdiv = document.getElementById(msgdivid);
  var handleSuccess = function(o) {
   if(o.responseText !== undefined) {
    res = eval('(' + o.responseText + ')');
    div.innerHTML = res['link'];
    msgdiv.innerHTML = '<p class="rm">' + res['msg'] + '</p>';}};
  var handleFailure = function(o) {
   var errordiv = document.getElementById("thread_rpc_feedback");
   errordiv.innerHTML = "<b>" + "ERROR." + "</b>";
   if(o.responseText !== undefined) {
    for (var n in o) {
     if (o.hasOwnProperty(n)) {
      errordiv.innerHTML += o[n];}}}
   window.location.href="#thread_rpc_feedback"};
  var callback = {
   success:handleSuccess,
   failure:handleFailure,
   argument:[]};
 msgdiv.innerHTML = "<b>Processing...</b>";
 var request = YAHOO.util.Connect.asyncRequest('POST', SNAPBOARD_URLS.rpc_action, callback, postData);}

// thread level functions
function set_csticky(id) { toggle_variable('csticky', 'csticky', 'thread', id, 'thread_rpc_feedback');}
function set_gsticky(id) { toggle_variable('gsticky', 'gsticky', 'thread', id, 'thread_rpc_feedback');}
function set_close(id) { toggle_variable('close', 'close', 'thread', id, 'thread_rpc_feedback');}

// post level function
function s_w(id) { toggle_variable('watch', 'w' , 'post', id, ('prf' + id));}
function s_c(id) { toggle_variable('censor', 'c', 'post', id, ('prf' + id));}
function s_a(id) { toggle_variable('abuse', 'a', 'post', id, ('prf' + id));}

function get_ta() {
 return document.getElementById('add_post_div').elements['post'];}

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
