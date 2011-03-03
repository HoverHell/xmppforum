/*
Copyright (c) 2008, Yahoo! Inc. All rights reserved.
Code licensed under the BSD License:
http://developer.yahoo.net/yui/license.txt
version: 2.5.1
*/
YAHOO.util.Connect={

_formNode:null,
_sFormData:null,
_poll:{},
_timeOut:{},
_polling_interval:50,

startEvent:new YAHOO.util.CustomEvent("start"),
completeEvent:new YAHOO.util.CustomEvent("complete"),
successEvent:new YAHOO.util.CustomEvent("success"),
failureEvent:new YAHOO.util.CustomEvent("failure"),
uploadEvent:new YAHOO.util.CustomEvent("upload"),
abortEvent:new YAHOO.util.CustomEvent("abort"),


setProgId:function(A){this._msxml_progid.unshift(A);},
setDefaultXhrHeader:function(A){if(typeof A=="string"){this._default_xhr_header=A;}else{this._use_default_xhr_header=A;}},
setPollingInterval:function(A){if(typeof A=="number"&&isFinite(A)){this._polling_interval=A;}},


_use_default_post_header:true,
_default_post_header:"application/x-www-form-urlencoded; charset=UTF-8",
setDefaultPostHeader:function(A){
 if(typeof A=="string"){
  this._default_post_header=A;}
 else{
  if(typeof A=="boolean"){
   this._use_default_post_header=A;}}},


_default_headers:{},
_http_headers:{},
_has_default_headers:true,
_has_http_headers:false,
initHeader:function(A,D,C){
 var B=(C)?this._default_headers:this._http_headers;
 B[A]=D;
 if(C){
  this._has_default_headers=true;}
 else{
  this._has_http_headers=true;}},
//=========================================================================================
_isFileUpload:false,

_msxml_progid:["Microsoft.XMLHTTP","MSXML2.XMLHTTP.3.0","MSXML2.XMLHTTP"],
_customEvents:{
onStart:["startEvent","start"],
onComplete:["completeEvent","complete"],
onSuccess:["successEvent","success"],
onFailure:["failureEvent","failure"],
onUpload:["uploadEvent","upload"],
onAbort:["abortEvent","abort"]},
_isFormSubmit:false,
asyncRequest:function(F,C,E,A){
 var D=(this._isFileUpload)?this.getConnectionObject(true):this.getConnectionObject();
 var B=(E&&E.argument)?E.argument:null;
 if(!D){
  return null;}
 else{
  if(E&&E.customevents){
   this.initCustomEvents(D,E);}
  if(this._isFormSubmit){
   if(this._isFileUpload){
    this.uploadFile(D,E,C,A);
    return D;}
   if(F=="GET"){
    if(this._sFormData.length!==0){
     C+=((C.indexOf("?")==-1)?"?":"&")+this._sFormData;}}
    else{
     if(F=="POST"){
      A=A?this._sFormData+"&"+A:this._sFormData;}}}
  if(F=="GET"&&(E&&E.cache===false)){
   C+=((C.indexOf("?")==-1)?"?":"&")+"rnd="+new Date().valueOf().toString();}
  D.conn.open(F,C,true);
  if(this._use_default_xhr_header){
   if(!this._default_headers["X-Requested-With"]){
    this.initHeader("X-Requested-With",this._default_xhr_header,true);}}
  if((F=="POST"&&this._use_default_post_header)&&this._isFormSubmit===false){
   this.initHeader("Content-Type",this._default_post_header);}
  if(this._has_default_headers||this._has_http_headers){this.setHeader(D);}
  this.handleReadyState(D,E);D.conn.send(A||"");
  if(this._isFormSubmit===true){this.resetFormState();}
  this.startEvent.fire(D,B);
  if(D.startEvent){D.startEvent.fire(D,B);}
  return D;}},


_transaction_id:0,
getConnectionObject:function(A){
 var C;
 var D=this._transaction_id;
 try{
  if(!A){
   C=this.createXhrObject(D);}
  else{
   C={};
   C.tId=D;C.isUpload=true;}
  if(C){
   this._transaction_id++;}}
 catch(B){}
 finally{return C;}},

createXhrObject:function(E){
 var D,A;
 try{
  A=new XMLHttpRequest();
  D={conn:A,tId:E};}
  catch(C){
   for(var B=0;B<this._msxml_progid.length;++B){
    try{
     A=new ActiveXObject(this._msxml_progid[B]);
     D={conn:A,tId:E};break;}
    catch(C){}}}
  finally{return D;}},
  
initCustomEvents:function(A,C){
 for(var B in C.customevents){
  if(this._customEvents[B][0]){
   A[this._customEvents[B][0]]=new YAHOO.util.CustomEvent(this._customEvents[B][1],(C.scope)?C.scope:null);
   A[this._customEvents[B][0]].subscribe(C.customevents[B]);}}},

setHeader:function(A){
 if(this._has_default_headers){
  for(var B in this._default_headers){
  if(YAHOO.lang.hasOwnProperty(this._default_headers,B)){
   A.conn.setRequestHeader(B,this._default_headers[B]);}}}
 if(this._has_http_headers){
  for(var B in this._http_headers){
   if(YAHOO.lang.hasOwnProperty(this._http_headers,B)){
    A.conn.setRequestHeader(B,this._http_headers[B]);}}
  delete this._http_headers;
  this._http_headers={};
  this._has_http_headers=false;}},

handleReadyState:function(C,D){
 var B=this;
 var A=(D&&D.argument)?D.argument:null;
 if(D&&D.timeout){
  this._timeOut[C.tId]=window.setTimeout(function(){
   B.abort(C,D,true);},
  D.timeout);}
 this._poll[C.tId]=window.setInterval(function(){
  if(C.conn&&C.conn.readyState===4){
   window.clearInterval(B._poll[C.tId]);
   delete B._poll[C.tId];
   if(D&&D.timeout){
    window.clearTimeout(B._timeOut[C.tId]);
    delete B._timeOut[C.tId];}
   B.completeEvent.fire(C,A);
   if(C.completeEvent){
    C.completeEvent.fire(C,A);}
    B.handleTransactionResponse(C,D);}},
 this._polling_interval);},


handleTransactionResponse:function(F,G,A){
 var D,C;
 var B=(G&&G.argument)?G.argument:null;
 try{
  if(F.conn.status!==undefined&&F.conn.status!==0){
   D=F.conn.status;}
  else{
   D=13030;}}
 catch(E){
  D=13030;}
 if(D>=200&&D<300||D===1223){
  C=this.createResponseObject(F,B);
  if(G&&G.success){
   if(!G.scope){
    G.success(C);}
  else{
   G.success.apply(G.scope,[C]);}}
  this.successEvent.fire(C);
  if(F.successEvent){
   F.successEvent.fire(C);}}
 else{switch(D){
  case 12002:case 12029:case 12030:case 12031:case 12152:case 13030:C=this.createExceptionObject(F.tId,B,(A?A:false));
  if(G&&G.failure){
   if(!G.scope){
    G.failure(C);}
   else{
    G.failure.apply(G.scope,[C]);}}
  break;
  default:C=this.createResponseObject(F,B);
  if(G&&G.failure){
   if(!G.scope){
    G.failure(C);}
   else{
    G.failure.apply(G.scope,[C]);}}}
  this.failureEvent.fire(C);
  if(F.failureEvent){
   F.failureEvent.fire(C);}}
 this.releaseObject(F);
 C=null;},
createResponseObject:function(A,G){
 var D={};
 var I={};
 try{
  var C=A.conn.getAllResponseHeaders();
  var F=C.split("\n");
  for(var E=0;E<F.length;E++){
   var B=F[E].indexOf(":");
   if(B!=-1){
    I[F[E].substring(0,B)]=F[E].substring(B+2);}}}
 catch(H){}D.tId=A.tId;
 D.status=(A.conn.status==1223)?204:A.conn.status;
 D.statusText=(A.conn.status==1223)?"No Content":A.conn.statusText;
 D.getResponseHeader=I;
 D.getAllResponseHeaders=C;
 D.responseText=A.conn.responseText;
 D.responseXML=A.conn.responseXML;
 if(G){
  D.argument=G;}
 return D;},
createExceptionObject:function(H,D,A){
 var F=0;
 var G="communication failure";
 var C=-1;
 var B="transaction aborted";
 var E={};
 E.tId=H;
 if(A){
  E.status=C;
  E.statusText=B;}
 else{
  E.status=F;
  E.statusText=G;}
 if(D){
  E.argument=D;}
 return E;},
};
