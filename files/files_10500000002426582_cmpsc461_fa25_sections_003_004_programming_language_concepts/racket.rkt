;this is my single line comment

#| this is my multi-line
comment in scheme |#

; Predicates: funs that evaluate to true or false
; convention: names of scheme predicates end in "?"
; number?: test whether argument is a number
;(number? 3)
;(number? "st")
;(boolean? #t)
;(string? "st")
;(positive? -11)

;(equal? 2 2)

; Operators: =, >, <, <=, >=
; = is only for numbers
;(= #t #t)
;(equal? #f #f)
; and, or, not
;(and (> 7 5) (> 10 20))


#| If expressions
   (if P E1 E2)
       eval P to a boolean, if it's true then eval E1, ese eval E2
|#

;( if (> 2 3) 4 "abc")
;(* 2 (if (> 2 3) 4 5))

;(define (max x y)(if (> x y) x y))

;(max 6 7)

;(define diverge (lambda (x) (diverge (+ x 1))))

;(define (f x) (if (> x 0) 0 (diverge x)))

;(f 1)
;(f -1)


;(define myeven? (lambda (n) (if (= n 0) #t (myodd? (- n 1)))))
;(define myodd? (lambda (n) (if (= n 0) #f (myeven? (- n 1)))))

;(myodd? 4)




#| Multi-Case

(Cond (P1 E1)
      ...
      (Pn En)
      (else En+1)

Problem: Write a function to assign a grade based on the value of test score. An A for a score of 90
or above, a B for a score of 80-89, a C for a score of 70-79, a D for 60-69, a F otherwise

|#


;(define (testscore x)
;  (cond ((>= x 90) 'A)
;        ((>= x 80) 'B)
;        ((>= x 70) 'C)
;        ((>= x 60) 'D)
;        (else 'F)
;    )

;  )


;(testscore 81)




#| Higher-Order Functions:
   that take functions as arguments
   return functions as results

   Check Slides

|#


;(define (twice f x) (f (f x)))
(define (plusOne x) (+ 1 x))
(define (square x) (* x x))

;(plusOne 3)
;(twice plusOne 2)
;(twice square 2)

;(twice (lambda (x) (+ x 2)) 3)

;(twice plusOne) 

;(define (twiceV2 f) (lambda (x) (f (f x))))

;((twiceV2 plusOne) 3)


;((lambda (x y) (+ x y)) 3 4)

;(((lambda (x) (lambda (y) (+ x y))) 3) 4)

; Let constructs

;(define x 0)
;(let ((x 2) (y x)) y)

;Let* constructs
;(define x 0)
;(let* ((x 2) (y x)) y)

; letrec

;(letrec
;  ((fact (lambda (n)
 ;           (if (= n 0) 1 (* n (fact (- n 1))))
  ;         )))
  ; (fact 3))



;(quote (+ 2 3))
;'pi


;List
;(define a 1)
;(define x (list 2 3 4 5 6))
;(null? x)
;(car x)
;(cdr x)
;(cons a x)


;(null? '())
;(car '(a))
;(cdr '(a))

(define x '((it seems that) you (like) me))
;(car x)
;(car (car x))
;(cdr (car x))
;(cdr x)
;(car (cdr x))
;(cdr (cdr x))
;(cadr x)



; Cons

;(cons 'a '())
;(cons '(a b (c)) '())
;(cons 'a (car '((b) c d)))
;(cons 'a (cdr '((b) c d)))

;(cons 'it (cons 'seems (cons 'that '())))
;'(it . (seems . (that . ())))
;(list 'it 'seems 'that)

; Length

;(define (lenght lst)
;  (cond ((null? lst) 0)
;     (else (+1 (length (cdr lst)))))

;  )

;(length '(a b c))
;(length '((a) b (a (b) c)))


; Append

;(define (apend l1 l2)
;  (if(null? l1) l2
;    (cons (car l1) (apend (cdr l1) l2))))

;(apend '(a b c) '(d))


; Member

(define (member? a lst)
  (cond ((null? lst) #f)
        ((equal? a (car lst)) #t)
        (else (member? a (cdr lst)))))

;(member? 3 '(1 3 2))
;(member? 'a '(a b c))
;(member? '(a) '((a) b c))

;map

(define (mapp f x)
  (if (null? x) '()
      (cons (f (car x)) (mapp f (cdr x)))))


;(mapp square '(1 2 3 4))
;(mapp plusOne '(3 7 8 9))

;(map (lambda (x) (> x 10)) '(3 7 12 9))
;(map (lambda (x) (if (even? x) 'Even 'Odd)) '(3 7 12 9))
;(map length '((a) (a b) (a b c) ()))

; Your Turn
;(map (lambda (x) (list x (+ x 1))) '(3 7 12 9))


; reduce

;(define (reduce f l v)
;  (if (null? l) v
;      (f (car l) (reduce f (cdr l) v))
;      )
;  )

;(reduce + '(2 4 6) 0)
;(reduce * '(2 4 6) 1)

;(reduce (lambda (x y) (and x y)) '(#t #f #t) #t)


; bind

;(define (bind key value env)
;  (cons (list key value) env)
;  )

;(bind 'd 4 '((a 1) (b 2) (c 3)))
;(bind 'a 10 '((a 1) (b 2) (c 3)))


;lookup

;(define (lookup key al)
;  (cond ((null? al) #f)
;        ((equal? key (caar al))(car al))
;        (else (lookup key (cdr al)))
;        )
;  )

;(lookup 'a '((a 1) (b 2) (a 3)))
;(lookup 'b '((a 1) (b 2) (a 3)))
;(lookup 'c '((a 1) (b 2) (a 3)))


;(define x '((a 1) (b 2) (a 3)))
;(caar x)
