import { useState, useEffect, useRef } from 'react';

interface UseTypingAnimationOptions {
  words: string[];
  typingSpeed?: number;
  deletingSpeed?: number;
  pauseDuration?: number;
}

export function useTypingAnimation({
  words,
  typingSpeed = 100,
  deletingSpeed = 50,
  pauseDuration = 2000,
}: UseTypingAnimationOptions) {
  const [currentWordIndex, setCurrentWordIndex] = useState(0);
  const [currentText, setCurrentText] = useState('');
  const [isDeleting, setIsDeleting] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    const currentWord = words[currentWordIndex];

    const handleTyping = () => {
      if (isPaused) {
        timeoutRef.current = setTimeout(() => {
          setIsPaused(false);
          setIsDeleting(true);
        }, pauseDuration);
        return;
      }

      if (isDeleting) {
        if (currentText.length === 0) {
          setIsDeleting(false);
          setCurrentWordIndex((prev) => (prev + 1) % words.length);
          timeoutRef.current = setTimeout(handleTyping, typingSpeed);
        } else {
          setCurrentText(currentWord.slice(0, currentText.length - 1));
          timeoutRef.current = setTimeout(handleTyping, deletingSpeed);
        }
      } else {
        if (currentText.length === currentWord.length) {
          setIsPaused(true);
          timeoutRef.current = setTimeout(handleTyping, pauseDuration);
        } else {
          setCurrentText(currentWord.slice(0, currentText.length + 1));
          timeoutRef.current = setTimeout(handleTyping, typingSpeed);
        }
      }
    };

    timeoutRef.current = setTimeout(handleTyping, isDeleting ? deletingSpeed : typingSpeed);

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [currentText, currentWordIndex, isDeleting, isPaused, words, typingSpeed, deletingSpeed, pauseDuration]);

  return currentText;
}

