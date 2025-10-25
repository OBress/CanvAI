#lang racket/base

#| Problem 1: Working with Data |#

(define (clamp-bounds ub lb data))
(define (cleanup-data data))
(define (lesser-decadents data))
(define (windowed-average size data))

; #| Problem 2: Dealing with Duration |#

(define (pad-duration duration))
(define (fmt-duration duration))
(define (add-durations leftDuration rightDuration))

; #| Problem 4: Curried Calculations |#

(define (calculate-subtotal order discounts))
