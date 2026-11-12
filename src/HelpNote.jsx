import React from 'react';
function textContent(value){return React.Children.toArray(value).map(child=>typeof child==='string'||typeof child==='number'?String(child):React.isValidElement(child)?textContent(child.props.children):'').join(' ');}
export function InlineNote({children}){const text=textContent(children).trim().replace(/\s+/g,' '),words=text.split(' ');return text?<small className="inline-note">{words.length>20?words.slice(0,20).join(' ')+'…':text}</small>:null;}
