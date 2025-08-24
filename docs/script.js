// Smooth scrolling for navigation links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Header scroll effect
window.addEventListener('scroll', () => {
    const header = document.querySelector('.header');
    if (header) {
        if (window.scrollY > 100) {
            header.style.background = 'rgba(0, 0, 0, 0.98)';
        } else {
            header.style.background = 'rgba(0, 0, 0, 0.95)';
        }
    }
});

// Animate elements on scroll
const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
};

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('animate-fade-in');
        }
    });
}, observerOptions);

// Observe all sections and cards when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Observe sections and cards for animation
    document.querySelectorAll('.section, .feature-card, .tool-card, .arch-component, .content-section, .api-section').forEach(el => {
        observer.observe(el);
    });
    
    // Set active navigation link based on current page
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';
    const navLinks = document.querySelectorAll('.nav-links a');
    navLinks.forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('href') === currentPage) {
            link.classList.add('active');
        }
    });
    
    // Mobile navigation toggle (if mobile menu exists)
    const navToggle = document.querySelector('.nav-toggle');
    const navLinks = document.querySelector('.nav-links');
    if (navToggle && navLinks) {
        navToggle.addEventListener('click', () => {
            navLinks.classList.toggle('active');
            navToggle.classList.toggle('active');
        });
    }
});

// Copy code blocks to clipboard
document.addEventListener('DOMContentLoaded', () => {
    const codeBlocks = document.querySelectorAll('.code-block, pre code');
    codeBlocks.forEach(block => {
        // Add copy button to code blocks
        const copyButton = document.createElement('button');
        copyButton.className = 'copy-btn';
        copyButton.innerHTML = '<i class="fas fa-copy"></i>';
        copyButton.title = 'Copy to clipboard';
        
        const container = document.createElement('div');
        container.className = 'code-container';
        block.parentNode.insertBefore(container, block);
        container.appendChild(copyButton);
        container.appendChild(block);
        
        copyButton.addEventListener('click', async () => {
            try {
                const text = block.textContent;
                await navigator.clipboard.writeText(text);
                copyButton.innerHTML = '<i class="fas fa-check"></i>';
                copyButton.style.color = '#10b981';
                setTimeout(() => {
                    copyButton.innerHTML = '<i class="fas fa-copy"></i>';
                    copyButton.style.color = '';
                }, 2000);
            } catch (err) {
                console.error('Failed to copy text: ', err);
            }
        });
    });
});

// Table of contents generation for documentation pages
document.addEventListener('DOMContentLoaded', () => {
    const contentSection = document.querySelector('.main-content');
    if (contentSection) {
        const headings = contentSection.querySelectorAll('h2, h3');
        if (headings.length > 2) {
            const toc = document.createElement('div');
            toc.className = 'table-of-contents';
            toc.innerHTML = '<h3>Table of Contents</h3><ul></ul>';
            
            const tocList = toc.querySelector('ul');
            headings.forEach((heading, index) => {
                const id = `heading-${index}`;
                heading.id = id;
                
                const li = document.createElement('li');
                li.className = heading.tagName.toLowerCase();
                const a = document.createElement('a');
                a.href = `#${id}`;
                a.textContent = heading.textContent;
                li.appendChild(a);
                tocList.appendChild(li);
            });
            
            // Insert TOC after the first paragraph or at the beginning
            const firstParagraph = contentSection.querySelector('p');
            if (firstParagraph) {
                firstParagraph.parentNode.insertBefore(toc, firstParagraph.nextSibling);
            } else {
                contentSection.insertBefore(toc, contentSection.firstChild);
            }
        }
    }
});