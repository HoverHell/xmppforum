function t_e(id) {
 toggle('pt'+id, 'block');
 exttoggle('replies', 'block', 'action=geteditform&oid='+id);
 return false;}
 
function t_r(id) {
 exttoggle('replies', 'block', 'action=getreplyform&oid='+id);
 return false;}

// thread level functions
function set_csticky(id) { exttoggle('replies', 'block', 'action=csticky&oclass=thread&oid='+id);}
function set_gsticky(id) { exttoggle('replies', 'block', 'action=gsticky&oclass=thread&oid='+id);}
function set_close(id) { exttoggle('replies', 'block', 'action=close&oclass=thread&oid='+id);}

// post level function
function s_w(id) { exttoggle('replies', 'block', 'action=watch&oclass=post&oid='+id);}
function s_c(id) { exttoggle('replies', 'block', 'action=censor&oclass=post&oid='+id);}
function s_a(id) { exttoggle('replies', 'block', 'action=abuse&oclass=post&oid='+id);}
 
function toggle(id, type) {
 var e = document.getElementById(id);
 if(e.style.display == 'none')
  e.style.display = type;
 else
  e.style.display = 'none';}

function exttoggle(id, type, action) { // on show retreives HTML code from RPC.
 var e = document.getElementById(id);
 if(e.style.display == 'none') {
  e.style.display = type;
  var handleSuccess = function(o) {
   if(o.responseText !== undefined) {
    res = JSON.parse(o.responseText);
    e.innerHTML = res.html;}};
  var handleFailure = function(o) {
   e.innerHTML = "<p>" + "ERROR." + "</p>";
   if(o.responseText !== undefined) {
    for (var n in o) {
     if (o.hasOwnProperty(n)) {
      e.innerHTML += o[n]+"<br/>";}}}};
  var callback = {
   success:handleSuccess,
   failure:handleFailure,
   argument:[]};
  e.innerHTML = "<p>" + "Processing..." + "</p>";
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

/*Hide|unhide thread */
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