// 브라우저 콘솔에 붙여넣기
// Dashboard 페이지의 구조를 분석하여 정확한 CSS 셀렉터 찾기

console.log("=== Dashboard 구조 분석 ===\n");

// 1. 타이틀 찾기
const title = document.querySelector('h1');
console.log("1. 타이틀:", title?.textContent);
console.log("   부모:", title?.parentElement?.getAttribute('data-testid'));

// 2. 타이틀의 다음 형제 요소들 찾기
let currentElement = title?.parentElement?.nextElementSibling;
let index = 1;
console.log("\n2. 타이틀 다음 요소들:");
while (currentElement && index <= 5) {
    const testId = currentElement.getAttribute('data-testid');
    const classes = currentElement.className;
    const tagName = currentElement.tagName;
    
    console.log(`   [${index}] ${tagName}`);
    if (testId) console.log(`       data-testid: ${testId}`);
    if (classes) console.log(`       class: ${classes}`);
    
    // HorizontalBlock(columns) 찾기
    if (testId === 'stHorizontalBlock') {
        console.log(`       >>> COLUMNS 블록 발견! <<<`);
        
        // 내부 column들 확인
        const columns = currentElement.querySelectorAll('[data-testid="column"]');
        console.log(`       내부 column 수: ${columns.length}`);
        
        columns.forEach((col, idx) => {
            console.log(`       - column[${idx}] 내용: ${col.textContent.substring(0, 50)}...`);
        });
    }
    
    // hr 찾기
    if (currentElement.querySelector('hr')) {
        console.log(`       >>> HR 발견! <<<`);
    }
    
    currentElement = currentElement.nextElementSibling;
    index++;
}

// 3. CSS 셀렉터 생성
console.log("\n3. 추천 CSS 셀렉터:");

// main 컨테이너 찾기
const main = document.querySelector('.main');
const blockContainer = document.querySelector('[data-testid="stAppViewContainer"] .main .block-container');

console.log(`   main 존재: ${!!main}`);
console.log(`   block-container 존재: ${!!blockContainer}`);

// HorizontalBlock 모두 찾기
const allHorizontalBlocks = document.querySelectorAll('[data-testid="stHorizontalBlock"]');
console.log(`\n4. 전체 HorizontalBlock 수: ${allHorizontalBlocks.length}`);

allHorizontalBlocks.forEach((block, idx) => {
    const text = block.textContent.substring(0, 100);
    console.log(`   [${idx}] ${text}...`);
    
    // 이것이 "마지막 업데이트" 블록인지 확인
    if (text.includes('마지막 업데이트') || text.includes('KRW')) {
        console.log(`       >>> 타겟 블록 발견! (인덱스: ${idx}) <<<`);
        
        // 부모 체인 출력
        let parent = block.parentElement;
        let level = 1;
        console.log(`       부모 체인:`);
        while (parent && level <= 5) {
            const testId = parent.getAttribute('data-testid');
            const classes = parent.className;
            console.log(`         [${level}] ${parent.tagName} ${testId ? `data-testid="${testId}"` : ''} ${classes ? `class="${classes}"` : ''}`);
            parent = parent.parentElement;
            level++;
        }
        
        // 다음 형제 요소 확인 (hr이 있는지)
        let nextSibling = block.nextElementSibling;
        console.log(`\n       다음 형제 요소:`);
        let siblingIndex = 1;
        while (nextSibling && siblingIndex <= 3) {
            const testId = nextSibling.getAttribute('data-testid');
            const hasHr = nextSibling.querySelector('hr') ? '>>> HR 포함 <<<' : '';
            console.log(`         [${siblingIndex}] ${nextSibling.tagName} ${testId ? `data-testid="${testId}"` : ''} ${hasHr}`);
            nextSibling = nextSibling.nextElementSibling;
            siblingIndex++;
        }
    }
});

// 5. 현재 적용된 스타일 확인
console.log("\n5. 현재 적용된 margin-bottom 스타일:");
allHorizontalBlocks.forEach((block, idx) => {
    const computedStyle = window.getComputedStyle(block);
    const marginBottom = computedStyle.marginBottom;
    console.log(`   [${idx}] margin-bottom: ${marginBottom}`);
});

console.log("\n=== 분석 완료 ===");
console.log("\n생성할 CSS 셀렉터 (위 정보 기반):");
console.log(`
/* 방법 1: nth-of-type 사용 */
[data-testid="stHorizontalBlock"]:nth-of-type(1) {
    margin-bottom: -1rem !important;
}

/* 방법 2: 텍스트 포함 여부로 선택 (JavaScript 필요) */
/* 이 경우 CSS만으로는 불가능 */

/* 방법 3: block-container 직계 자식 중 첫 번째 HorizontalBlock */
.block-container > div > [data-testid="stHorizontalBlock"]:first-child {
    margin-bottom: -1rem !important;
}
`);
