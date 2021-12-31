#!/usr/bin/env python
# Copyright (C) 2013-2016 Shea G Craig
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


"""barbell

An object-oriented framework for designing barbell training programs.

Barbell makes the generation of training programs for groups of athletes
concise, flexible, and pythonic. Classes represent individual Lifts or
exercises, Elements of workouts, entire workout Sessions, Microcycles
consisting of any number of Sessions, and Macrocycles built upon
Microcycles. Each class has a variety of overrideable public attributes
for contolling progression and variation over the course of the training
plan. Further, each type can be used on its own, or only during
configuration as part of a higher-order type like Microcycle.
"""


class Lift(object):

    def __init__(self, lift_type, personal_record, training_max=None,
                 increment=10.0, barbell_weight=45.0):
        self.lift_type = lift_type
        self.personal_record = personal_record
        if training_max:
            if training_max <= 1 and training_max >= 0:
                # Training max is a percentage of the PR.
                # TODO: Round to nearest plate size.
                self.training_max = training_max * personal_record
            else:
                # Training max is a raw number.
                self.training_max = training_max
        else:
            # No training max supplied, so use PR.
            self.training_max = personal_record

        self.increment = increment
        self.barbell_weight = barbell_weight

    def increase_training_max(self):
        if self.training_max and self.increment:
            self.training_max += self.increment


class Element(object):
    """A single element of a workout with logic for modulation.

    Attributes:
        load_coefficients (list of sequences of floats, str, or None):
            The load_coefficients determine both the number of
            sessions to generate through a complete cycle and the
            number of sets for each session. Thus, it cannot be simply
            None (i.e. load_coefficients = []). Please read the full
            docstring to understand the interaction between
            load_coefficients and schemes.

            The type of load_coefficients must be a list.
            The list can be any length greater than zero, and must be
            composed of sequences of floats, strings, or None.

            A float value will be multipled against the Element's lift's
            training max to determine a load for that set.

            A string or None will be output as-is.

            e.g.:
                [(0.65, 0.75, 0.85), (0.7, 0.8, 0.9))]
            would represent the first two sessions of a Wendler 531 lift.
            The first session consists of 3 sets, at 65%, 75%, and 85%,
            and the second session 3 sets of 70%, 80%, and 90%.

                [(0.7, 0.7, 0.7, 0.75, 0.75, 0.75, 0.8, 0.8)]
            would represent an Olympic Snatch day consisting of
            70% x 1 x 3, 75% x 1 x 3, and 80% x 1 x 2 (provided the
            scheme attribute is set to [(1,)]

            Keep in mind, it is not the responsibility of an Element
            to collapse the above into "70% x 1 x 3" for output; if
            desired, that can be done by the renderer or templating
            system.

                [("Max for day"), ("Max for day"), ("Max for day")]
            would represent three weeks of an element requesting you
            lift up to a max for the day. With a scheme of [(1,)], you
            would get a max single for the day.

        scheme (list of sequences of ints or strings): Each element of
            scheme should be a sequence of integers describing the number
            of reps to perform, or strings describing more complex
            set and rep schemes.

            An integer is interpreted literally as a number of reps.

            A string is returned as provided, allowing the coach to
            prescribe more complex schemes like "1.1.1", "2+", or "2+1".

            You may not have a None value.

            If the length of the scheme list is less than the length of
            the load_coefficients, it will be repeated after it has been
            exhausted.

            Likewise, if a session sequence from scheme is shorter than
            the length of the load_coefficients for that session, the
            pattern will be repeated until all loads are calculated.

            Extra schemes or session schemes beyond the length of the
            load_coefficients are ignored.

        training_max_modulation: None or List enclosing sequences. Each
            sequence should consist of:
                int frequency: Number of sessions to wait before
                    increasing the training max.
                int amount or None: Amount of weight to add to training
                    max after the frequency period has expired.

            This is primarily useful for Wendler 531 programming.
            Percentage based programs, like an Olympic program, will
            probably want to just specify a longer load_coefficients
            list.

            e.g. For Wendler, bump a lift's training max by 10 every 3
            weeks for two microcycles, and then by 0 for a 1 week
            microcycles (deload week).
                training_max_modulation = [(3, 10), (3, 10), (1, 0)]

        To program an Element with no load, provide None for
        each session, and a single "scheme" value
        describing the sets and reps.
        e.g. for a 3 session cycle of 5x10:
            load_coefficients = [[None], [None], [None]]
            scheme = [("5 x 10",)]

        Similarly, to program an Element with a constant load
        (sets across), provide a load_coefficient for each desired
        session and a string rep scheme to correspond.
        e.g. for a 3 session cycle of 70% x 5 x 5, 75% x 5 x 5,
        80% x 5 x 5:
            load_coefficients = [[0.7], [0.75], [0.80]]
            scheme = [("5 x 5")]
    """

    load_coefficients = []
    scheme = []
    training_max_modulation = []

    def __init__(self, lift):
        self.lift = lift
        # TODO: Keep or no?
        # if (not isinstance(self.load_coefficients, list) or
        #         any(item is None or len(item) == 0 for item in
        #             self.load_coefficients) or
        #         len(self.load_coefficients) == 0):
        #     raise AttributeError(
        #         "You may not have a load_coefficient session of 'None'")

        self.session_index = 0
        self.load_coefficient_index = 0
        self.scheme_index = 0

    def __iter__(self):
        return self

    def __next__(self):
        # load_coefficients ultimately determine the number of unique
        # sessions.
        if self.load_coefficient_index == len(self.load_coefficients):
            #raise StopIteration
            self.load_coefficient_index = 0

        loads = self.load_coefficients[self.load_coefficient_index]
        load_queue = []
        for load in loads:
            if isinstance(load, float):
                load = round_weight(load * self.lift.training_max,
                                    barbell_weight=self.lift.barbell_weight)
            load_queue.append(load)
        self.load_coefficient_index += 1

        if self.scheme_index == len(self.scheme):
            self.scheme_index = 0
        scheme = self.scheme[self.scheme_index]
        self.scheme_index += 1

        scheme_scale = int(len(load_queue) / len(scheme))
        if len(load_queue) % len(scheme) > 0:
            scheme_scale += 1
        scheme_queue = scheme * scheme_scale

        return (self.lift.lift_type, list(zip(load_queue, scheme_queue)))


class Session(object):
    """Represents a series of training sessions."""

    elements = []
    name = "Session"

    def __init__(self, lifts):
        self.element_generators = []
        #for element, element_lift in self.elements:
        for element in self.elements:
            if not isinstance(element[0], list):
                element_type = element[0]
                element_lift = element[1]
                for lift in lifts:
                    if lift.lift_type == element_lift:
                        self.element_generators.append(element_type(lift))
            else:
                # TODO: recurse
                sub_elements = []
                for sub_element in element:
                    element_type = sub_element[0]
                    element_lift = sub_element[1]
                    for lift in lifts:
                        if lift.lift_type == element_lift:
                            sub_elements.append(element_type(lift))

                self.element_generators.append(sub_elements)
        self.lifts = lifts

    def __len__(self):
        return max(len(item.load_coefficients) for item in self.elements)

    def __iter__(self):
        return self

    def __next__(self):
        result = []
        for element in self.element_generators:
            if isinstance(element, list):
                sub_result = []
                for sub_element in element:
                    sub_result.append(next(sub_element))
                result.append(sub_result)
            else:
                result.append(next(element))
        return (self.name, result)


class Microcycle(object):
    '''Represents a series sessions as a microcycle of lifting.

    Includes methods for managing training load increases and deviations
    from the patterns configured in Elements.
    '''
    training_max_modulation = [None]
    sessions = []
    length = 0

    def __init__(self, lifts):
        self.mod_index = 0
        self.session_counter = 0
        self.lifts = lifts
        self._sessions = []
        for session in self.sessions:
            self._sessions.append(session(self.lifts))

    def generate_cycle(self):
        # TODO: Nope
        cycle = []
        for counter in range(self.length):
            sessions = []
            for session in self._sessions:
                sessions.append(next(session))
            cycle.append(sessions)

        result = self.get_metadata()
        result["cycle"] = cycle

        return result

    def get_metadata(self):
        """Return a dict of information from this cycle"""
        result = {}
        meta_types = ("name", "training_maxes", "personal_records", "notes")
        for meta in meta_types:
            if hasattr(self, meta):
                result[meta] = getattr(self, meta)

        return result

    @property
    def training_maxes(self):
        return {lift.lift_type: lift.training_max for lift in self.lifts}

    @property
    def personal_records(self):
        return {lift.lift_type: lift.personal_record for lift in self.lifts}

    def increase_training_maxes(self):
        for lift in self.lifts:
            lift.increase_training_max()

        # # Handle bumping up training max if it is configured.
        # # TODO: Better arg handling
        # if self.training_max_modulation:
        #     # If this Element uses training max increases, check to
        #     # see if one is due.
        #     freq, mod_amt = self.training_max_modulation[self.mod_index]

        #     if self.session_counter == freq - 1:
        #         # TODO: Bump up primary lift
        #         # for lift in [session.elements[0].lift for session in self.sessions]:
        #         #     lift.increase_training_max(mod_amt)
        #         # TODO: Doesn't handle variable increases (get from lift)
        #         for lift in self.lifts:
        #             lift.training_max += mod_amt
        #         self.session_counter = 0

        #         # If we have consumed the modulation list, reset the
        #         # index to begin at the start again.
        #         self.mod_index += 1
        #         if self.mod_index == len(self.training_max_modulation):
        #             self.mod_index = 0
        #     else:
        #         self.session_counter += 1



# Subclasses

class WendlerSomething(Element):
    load_coefficients = [
        (0.65, 0.75, 0.85), (0.7, 0.8, 0.9), (0.75, 0.85, 0.95)]
    scheme = [
        (5, 5, "5+"), (3, 3, "3+"), (5, 3, "1+")]
    # TODO: Maybe move the modulation to after the deload week?
    # After 3 session increase by 10, 3 more, increase by 10, then the
    # deload week do nothing.
    training_max_modulation = [(3, 10), (3, 10), (1, 0)]


class WendlerDeloadSomething(Element):
    load_coefficients = [(0.40, 0.50, 0.60)]
    scheme = [(5, 5, 5)]


class JokerSomething(Element):
    load_coefficients = [
        ("+5-10% Joker", "+5-10% Joker"), ("+5-10% Joker", "+5-10% Joker"),
        ("+5-10% Joker",)]
    scheme = [
        (5, 1), (3, 1), (1,)]
    # TODO: Maybe move the modulation to after the deload week?
    # After 3 session increase by 10, 3 more, increase by 10, then the
    # deload week do nothing.
    training_max_modulation = [(3, 10), (3, 10), (1, 0)]


class FirstSetLastSomething(Element):
    load_coefficients = [(0.65,), (0.70,), (0.75,)]
    scheme = [("3-5 sets of 5-8 reps",)]


class AccessoryLift(Element):
    load_coefficients = [(None,)]
    scheme = [("5 sets of 10",)]


class CoreWork(Element):
    load_coefficients = [(None,)]
    scheme = [("5 sets of 10-20",)]


# Helper funcs

def round_weight(weight, barbell_weight=45.0, precision=None):
    """Round a weight to the nearest loadable plate combination.

    This function makes some guesses about minimum plate size if one
    isn't specified based on the barbell_weight value. Not everyone
    may have access to fractionals, so you may have to specify the
    precision to meet your needs.

    If you just want to avoid micro-loading, set the precision to the
    smallest increment you want to use.

    Note: The math is the same for kilos or pounds. If you are working
    in kilos, make sure to specify the barbell_weight in kilos, and
    specify the precision needed, and vice versa.

    e.g. round_weight(103.5) = 105
         round_weight(103.5, 2.0) = 104
         round_weight(101.5) = 100
         Imperial Women's Bar:
         round_weight(101, barbell_weight=33) = 103
         Kilos:
         round_weight(101.7, barbell_weight=20) = 102
         Kilos, but with no fractionals:
         round_weight(101.7, barbell_weight=20, precision=5.0) = 100

    Args:
        weight (number): The weight to round to the nearest plate combo.
        barbell_weight (number): The weight of the barbell in the same
            units as the rounded weight. It defaults to the fantasy
            value of 45.0 which everyone uses even though standard bars
            are actually 20kg/44lbs.
        precision (number): The smallest increment available for plate
            changes. If a barbell_weight is specified that looks like it
            is in pounds, it defaults to "5.0" (33, 35, 44, or 45 or
            float equivalents), otherwise it uses "1.0".

    Returns:
        Float rounded weight value to the nearest plate combination
        loadable for that bar. If the weight is less than the bar, the
        weight of the bar is returned.
    """
    plate_weight = weight - barbell_weight
    if not precision:
        # Consider weights to be in pounds if bar weight is specified
        # as either the correct weight or the rounded convenience
        # weight.
        # Likewise, assume that 2.5's are the smallest weights
        # available for imperial folks, and 1/2 kilo fractionals for
        # kilo users.
        if float(barbell_weight) in (33.0, 35.0, 44.0, 45.0):
            precision = 5.0
        else:
            precision = 1.0
    base = int(plate_weight / precision) * precision
    rounded_up = base + precision
    delta_down = plate_weight - base
    delta_up = rounded_up - plate_weight
    return barbell_weight + (base if delta_down < delta_up else rounded_up)
