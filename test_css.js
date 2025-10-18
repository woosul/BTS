// 브라우저 콘솔에 붙여넣어서 실행
// 현재 적용된 스타일과 여백을 확인

console.log("=== Dashboard 여백 분석 ===\n");

// 1. 첫 번째 HorizontalBlock 찾기
const verticalBlock = document.querySelector('[data-testid="stVerticalBlock"]');
console.log("1. stVerticalBlock 존재:", !!verticalBlock);

if (verticalBlock) {
    const layoutWrapper = verticalBlock.querySelector('[data-testid="stLayoutWrapper"]');
    console.log("2. 첫 번째 stLayoutWrapper 존재:", !!layoutWrapper);
    
    if (layoutWrapper) {
        const horizontalBlock = layoutWrapper.querySelector('[data-testid="stHorizontalBlock"]');
        console.log("3. stHorizontalBlock 존재:", !!horizontalBlock);
        
        if (horizontalBlock) {
            const computed = window.getComputedStyle(horizontalBlock);
            console.log("\n현재 적용된 스타일:");
            console.log("  - margin-top:", computed.marginTop);
            console.log("  - margin-bottom:", computed.marginBottom);
            console.log("  - padding-top:", computed.paddingTop);
            console.log("  - padding-bottom:", computed.paddingBottom);
            
            // 테스트: margin-bottom을 -1rem으로 강제 설정
            console.log("\n🧪 테스트: margin-bottom을 -1rem으로 설정");
            horizontalBlock.style.marginBottom = "-1rem";
            horizontalBlock.style.marginTop = "0";
            horizontalBlock.style.paddingTop = "0";
            horizontalBlock.style.paddingBottom = "0";
            
            console.log("✅ 스타일 강제 적용 완료!");
            console.log("   변화가 있나요? 없으면 다른 요소가 여백을 만들고 있습니다.");
        }
    }
}

// 2. 타이틀과 columns 사이의 요소들 확인
console.log("\n=== 타이틀과 Columns 사이 요소 분석 ===");
const title = document.querySelector('h1');
if (title) {
    const titleParent = title.closest('[data-testid="stElementContainer"]');
    console.log("타이틀 컨테이너:", titleParent);
    
    let nextElement = titleParent.nextElementSibling;
    let index = 1;
    
    console.log("\n타이틀 다음 요소들:");
    while (nextElement && index <= 10) {
        const testId = nextElement.getAttribute('data-testid');
        const computed = window.getComputedStyle(nextElement);
        
        console.log(`\n[${index}] ${nextElement.tagName} ${testId ? `(${testId})` : ''}`);
        console.log(`  margin: ${computed.marginTop} / ${computed.marginBottom}`);
        console.log(`  padding: ${computed.paddingTop} / ${computed.paddingBottom}`);
        
        if (testId === 'stLayoutWrapper') {
            console.log("  >>> 이게 columns 부모입니다!");
            break;
        }
        
        nextElement = nextElement.nextElementSibling;
        index++;
    }
}

// 3. HR 요소 확인
console.log("\n=== HR 위치 확인 ===");
const hrs = document.querySelectorAll('hr');
if (hrs.length > 0) {
    const firstHr = hrs[0];
    const hrParent = firstHr.closest('[data-testid="stElementContainer"]');
    const computed = window.getComputedStyle(hrParent);
    
    console.log("첫 번째 HR의 부모 컨테이너:");
    console.log("  margin-top:", computed.marginTop);
    console.log("  margin-bottom:", computed.marginBottom);
    console.log("  padding-top:", computed.paddingTop);
    
    // 이전 형제 요소 확인
    const prevElement = hrParent.previousElementSibling;
    if (prevElement) {
        const prevTestId = prevElement.getAttribute('data-testid');
        const prevComputed = window.getComputedStyle(prevElement);
        console.log("\nHR 바로 위 요소:", prevTestId);
        console.log("  margin-bottom:", prevComputed.marginBottom);
        console.log("  padding-bottom:", prevComputed.paddingBottom);
    }
}

console.log("\n=== 분석 완료 ===");
console.log("위 정보를 공유해주세요!");
