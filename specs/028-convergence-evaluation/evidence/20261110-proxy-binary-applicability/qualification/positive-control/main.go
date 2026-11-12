package main
import("fmt";"os";"golang.org/x/net/html";"golang.org/x/crypto/openpgp")
// Intentionally affected scanner control. Compile/scan only; never execute.
func main(){
 if len(os.Args)>1&&os.Args[1]=="html" {
  node,err:=html.Parse(os.Stdin);if err!=nil{panic(err)}
  if err=html.Render(os.Stdout,node);err!=nil{panic(err)}
 }else{keys,err:=openpgp.ReadArmoredKeyRing(os.Stdin);fmt.Println(len(keys),err)}
}
