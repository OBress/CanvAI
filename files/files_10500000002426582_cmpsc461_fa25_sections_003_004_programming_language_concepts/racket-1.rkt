; define subs, which takes a b l, and replace a with b in l

(define (subs a b l)
  (if (null? l) '()
     (let ((rest (subs a b (cdr l))))
       (if (equal? (car l) a)
            (cons b rest)
            (cons (car l) rest)
           )
       )

      )
  )

;(subs 2 3 '(2 3 5 6 3 4 2))

(cons 3 (subs 2 3 '(3 5 6 3 4 2)))
        (cons 3 (subs 2 3 '(5 6 3 4 2)))
                (cons 5 (subs 2 3 '(6 3 4 2)))
                        (cons 6 (subs 2 3 '(3 4 2)))
                                (cons 3 (subs 2 3 '(4 2)))
                                        (cons 4 (subs 2 3 '(2)))
                                                (cons 3 (subs 2 3 '()))
                                                        ()


(define (lstSum-right init lst)
  (if (null? lst) init
      (+ (car lst) (lstSum-right init (cdr lst)))
      ))

;(lstSum-right 0 '(1 2 3))

(define (lstSum-left init lst)
  (if (null? lst) init
      (lstSum-left (+ init (car lst)) (cdr lst))
      )
  )


;(lstSum-left 0 '(1 2 3))


; uncurried version

(define (add m n)
        (+ m n)
  )

;(add 2 3)
;(add 2)
;(map (add 2) '(1 2 3))

; Curried version

(define(addN n)(lambda (m) (+ m n)))
;((addN 2) 3)
;(addN 2)
;(map (addN 2) '(1 2 3))

(define addM (lambda (x) (lambda (y) (+ x y))))
;((addM 2) 3)

;(define (cardMachine card pin request) (serve request))

;(define (cardMachine (lambda(card)
;                          (lambda(pin)
;                             (lambda(request)
;                                 (serve request))))))


;Partial Evaluation

(define (curry2 f)
    (lambda (x)
      (lambda (y)
        (f x y))))

;((curry2 add)2)

(define partial (addM 2))

;(partial 3)