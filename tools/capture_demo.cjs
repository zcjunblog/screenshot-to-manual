// Development-only screenshots of a running fictional demo, never substituted for user input.
const { chromium }=require('playwright');
const fs=require('fs'); const path=require('path');
(async()=>{
const browser=await chromium.launch({headless:true,channel:'chrome'});
const evidence=[];
for(const [name,width,height] of [['desktop',1200,850],['mobile',390,844]]){
 const page=await browser.newPage({viewport:{width,height},deviceScaleFactor:2});
 await page.goto('http://127.0.0.1:8769/');
 for(let i=1;i<=3;i++){
  if(i===2)await page.locator('#new').click();
  if(i===3){await page.locator('#item').fill('演示笔记本');await page.locator('#amount').fill('2');await page.locator('#submit').click();}
  const file=`examples/screenshots/${name}/${i}.png`;
  await page.screenshot({path:file,fullPage:true});
  const control=i===1?'#new':i===2?'#submit':'.success';
  const box=await page.locator(control).boundingBox();
  const owner=i===2?await page.locator('#owner').boundingBox():null;
  evidence.push({case:name,index:i,file,control,box,owner,pixel_ratio:2});
 }
 await page.close();
}
fs.copyFileSync('examples/screenshots/desktop/1.png','examples/screenshots/mixed/1.png');
fs.copyFileSync('examples/screenshots/mobile/2.png','examples/screenshots/mixed/2.png');
fs.copyFileSync('examples/screenshots/desktop/3.png','examples/screenshots/mixed/3.png');
fs.writeFileSync('examples/capture-record.json',JSON.stringify(evidence,null,2)+'\n');
await browser.close();console.log('Captured6screenshots of running demo;3mixed references copied.');
})().catch(e=>{console.error(e);process.exit(1)});
