(declare-const b Int)
(declare-const g Int)

(assert (= (- b 1) g))
(assert (= (* 2 (- g 1)) b))
(check-sat)
(get-model)
